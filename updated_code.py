from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import datetime
import pygame as pg
import threading
import keyboard as kb
import time
import json
import os
import sys

# JSON file to store latest messages
JSON_FILE = "latest_message.json"

# Initialize Selenium WebDriver
driver = webdriver.Chrome()
driver.get("https://web.whatsapp.com")

print("Please scan the QR code to log in to WhatsApp Web.")
time.sleep(30)

# Function to read JSON data or create the file if missing
def read_json():
    if not os.path.exists(JSON_FILE):  
        with open(JSON_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, indent=4, ensure_ascii=False)
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}

# Function to write updated data to JSON
def write_json(timestamp, message_text):
    data = read_json()
    if timestamp not in data:
        data[timestamp] = []  

    if message_text not in data[timestamp]:  
        data[timestamp].append(message_text)

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        

def get_today_messages(driver):
    try:
        # Find the "TODAY"/"HEUTE" label container
        today_label_container = driver.find_element(By.XPATH, '//div[@class="_amk4 _amkb"]/span[contains(text(), "HEUTE") or contains(text(), "TODAY")]')
        
        # Move to its parent and get all next sibling elements that contain messages
        today_container = today_label_container.find_element(By.XPATH, "./../..")  # Move up to the main wrapper div
        chat_containers = today_container.find_elements(By.XPATH, './following-sibling::div[@tabindex="-1"]')

        print(f"✅ Extracting {len(chat_containers)} messages from 'TODAY' section.")  # Debugging output
        return chat_containers  # Return only messages appearing after "TODAY"

    except Exception as e:
        print(f"⚠️ Error finding 'TODAY' section: {e}")
        return []  # Return empty list if "TODAY" isn't found


def get_visible_chat(driver):
    chat_containers = get_today_messages(driver)  # Get only today's messages

    if not chat_containers:  # Ensure we're checking only today's messages
        sys.stdout.write("\r⚠️ No messages found TODAY. Waiting for new messages...")
        sys.stdout.flush()
        return None, None

    latest_time_diff = float("inf")
    latest_message = None
    latest_timestamp = None

    for chat in chat_containers:
        try:
            # Extract **all spans** inside the message container (Handles multi-line messages)
            message_elements = chat.find_elements(By.XPATH, './/span[@dir="ltr"][@class="_ao3e selectable-text copyable-text"]/span')
            message_text = "\n".join([span.text.strip() for span in message_elements if span.text.strip()])  # Join spans with newline
            print("Extracted Message:", message_text)  # Debugging output

            # Move **1 level up** and find the **sibling timestamp container**
            timestamp_elements = chat.find_elements(By.XPATH, './/span[@class="x1rg5ohu x16dsc37"]')
            timestamp_text = timestamp_elements[-1].text.strip() if timestamp_elements else None  # Pick the last timestamp
            print("Extracted Timestamp:", timestamp_text)  # Debugging output

            # Convert timestamp to datetime
            if timestamp_text:
                message_time = datetime.strptime(timestamp_text, "%I:%M %p")
                current_time = datetime.now()
                time_diff = abs((current_time.hour * 60 + current_time.minute) - (message_time.hour * 60 + message_time.minute))

                if time_diff < latest_time_diff:
                    latest_time_diff = time_diff
                    print(f"Latest Time Difference: {latest_time_diff}min")  # Debugging output
                    print(f"Latest Message: {message_text}")  # Debugging output
                
                # Check if this is the most recent message within 1 minute
                if time_diff <= 1 and time_diff < latest_time_diff:
                    latest_time_diff = time_diff
                    latest_message = message_text
                    latest_timestamp = timestamp_text

        except Exception as e:
            print(f"⚠️ Error extracting message or timestamp: {e}")
            continue  # Skip any errors and move to the next message

    return latest_timestamp, latest_message


# Function to process message text (modify based on logic)
def process_text(msg_text):
    schichts = ('spätschicht', 'frühschicht')
    tage = ('jetzt', 'heute', 'morgen', 'samstag', 'sonntag', 'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag')
    msg_text = msg_text.lower()
    ans = False
    s = []
    t = []
    simple_mode = False

    for schicht in schichts:
        if any((all(l in msg_text for l in ('mitarbeiter', 'benötigen', schicht)), 
                all(s1 in msg_text for s1 in ('wer kann', schicht)), 
                all(s2 in msg_text for s2 in ('kann', 'jemand', schicht)))):

            if not simple_mode:
                for tag in tage:
                    if tag in msg_text and tag not in t:
                        t.append(tag)

            s.append(schicht)
            ans = True

    if ans:
        msg = 'Ich kann jeden Tag Frühschicht oder Spätschicht arbeiten.' if simple_mode else 'Ich kann {} {} arbeiten.'.format(', '.join(t), ' oder '.join(s))
        return ans, msg

    return ans, " "


audio_playing = False
audio_lock = threading.Lock()

def play_audio(audio_file):
    """Continuously plays the alarm until 'q' is pressed."""
    global audio_playing
    pg.mixer.init()
    pg.mixer.music.load(audio_file)
    
    with audio_lock:
        if audio_playing:
            return  # Prevent multiple instances from playing

        audio_playing = True

    try:
        while audio_playing:
            pg.mixer.music.play()
            sys.stdout.write("\r🔊 Alarm playing... Press 'q' to stop.")
            time.sleep(15)  # Replay every 15 seconds
    finally:
        stop_audio()

def stop_audio():
    """Stops the alarm sound."""
    global audio_playing
    with audio_lock:
        audio_playing = False
    pg.mixer.music.stop()
    print("\n🔕 Audio stopped.")

def listen_for_stop():
    """Listens for the 'q' key to stop the audio."""
    if audio_playing:
        print("Press 'q' to stop the audio.")
        kb.wait('q')
        stop_audio()


# Continuously monitor for new messages
while True:
    latest_timestamp, latest_message = get_visible_chat(driver)

    if latest_timestamp and latest_message:
        last_saved_data = read_json()

        # Print the most recent message **EVERY iteration**
        sys.stdout.write(f"\r⏳ Latest message in viewport: '{latest_message}' at {latest_timestamp}   ")
        sys.stdout.flush()

        # Process and respond only if it's a new message
        if latest_message not in last_saved_data.get(latest_timestamp, []):
            answerable, response = process_text(latest_message)

            if answerable:
                sys.stdout.write(f"\r🔔 New message detected: '{latest_message}' at {latest_timestamp}   ")
                sys.stdout.flush()
                write_json(latest_timestamp, latest_message)

                try:
                    msg_box = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'))
                    )
                    msg_box.send_keys(response)
                    msg_box.send_keys(Keys.RETURN)


                    # Start the alarm if it's not already playing
                    if not audio_playing:
                        play_audio_thread = threading.Thread(target=play_audio, args=("digital-alarm-clock-151920.mp3",), daemon=True)
                        play_audio_thread.start()
                        # Start a separate thread for 'q' key listening
                        stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
                        stop_thread.start()
                except:
                    pass

    time.sleep(5)