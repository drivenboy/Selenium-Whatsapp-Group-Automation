from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import json
import pygame as pg
import keyboard as kb
import sys
import threading
import os

# JSON file to store latest messages
JSON_FILE = "latest_message.json"

# Function to read existing JSON data or create the file if missing
def read_json():
    if not os.path.exists(JSON_FILE):  # Check if file exists
        with open(JSON_FILE, "w") as file:
            json.dump({}, file, indent=4)  # Create empty JSON file
    try:
        with open(JSON_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}  # Return empty dict if file is corrupted

# Function to write updated data to JSON
def write_json(timestamp, message_text):
    data = read_json()  # Load existing messages
    if timestamp not in data:
        data[timestamp] = []  # Initialize list if timestamp is new

    if message_text not in data[timestamp]:  # Prevent duplicate storage
        data[timestamp].append(message_text)  

    with open(JSON_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
        file.flush()  # Ensures immediate write to file

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
            time.sleep(5)  # Replay every 5 seconds
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
    print("Press 'q' to stop the audio.")
    kb.wait('q')
    stop_audio()

# Function to check if a "TODAY" label exists in the chat
def check_today_label():
    max_attempts = 5  # Limit retries
    attempt = 0

    while attempt < max_attempts:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main"]'))
            )

            for A in range(1, 101):  # Iterate over up to 100 elements
                today_xpath = f'//*[@id="main"]/div[3]/div/div[2]/div[3]/div[{A}]/div/span'
                try:
                    today_element = driver.find_element(By.XPATH, today_xpath)

                    if today_element.text.strip().lower() == "today":
                        sys.stdout.write("\r✅ 'TODAY' label found. Proceeding to check messages...\n")
                        sys.stdout.flush()
                        return  # Exit when "TODAY" is found

                except Exception:
                    continue  # Try next possible XPath

        except Exception:
            sys.stdout.write(f"\r Attempt {attempt + 1}: 'TODAY' not found, retrying...\n")
            sys.stdout.flush()

        attempt += 1
        time.sleep(2)  # Wait before retrying

    sys.stdout.write("\r🔄 Refreshing page and retrying...\n")
    sys.stdout.flush()
    driver.refresh()  # Refresh WhatsApp Web and retry
    time.sleep(10)

def process_text(msg_text):
    schichts = ('spätschicht', 'frühschicht')
    tage = ('jetzt', 'heute', 'morgen', 'samstag', 'sonntag', 'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag')
    ans = False
    s=[]
    t=[]
    simple_mode = True
    for schicht in schichts:
        if any((all(l in msg_text for l in ('mitarbeiter', 'benötigen', schicht)), all(s1 in msg_text for s1 in ('wer kann', schicht)), all(s2 in msg_text for s2 in ('kann', 'jemand', schicht)))):
            if not simple_mode:
                for tag in tage:
                    if tag in msg_text and tag not in t:
                        t.append(tag)
                        print("Added tag:", tag)
                    else:
                        print("Skipped tag:", tag)

            s.append(schicht)
            ans = True
            
    t_string = ''
    s_string = ''    

    if ans:
        if not simple_mode:
            for i in range(len(t)):
                if len(t)>1:
                    if i<len(t)-1:
                        t_string += t[i]+', '
                    else:
                        t_string += 'und '+t[i]
                else:
                    t_string += t[0]
            print(f"The days are {t_string}")

            for i in range(len(s)):
                if len(s)>1:
                    if i<len(s)-1:
                        s_string += s[i]+', '
                    else:
                        s_string += 'oder '+s[i]
                else:
                    s_string += ' '+s[0]
    
        msg = 'Ich kann ' +t_string+' '+s_string+' arbeiten.' if not simple_mode else 'Ich kann jeden Tag Frühschicht oder Spätschicht arbeiten.'
        return ans, msg
    
    else:
        return ans, " "

# Initialize Chrome driver
driver = webdriver.Chrome()

# Open WhatsApp Web
baseurl = "https://web.whatsapp.com"
driver.get(baseurl)

# Wait for QR Code scan
print("Please scan the QR code to log in to WhatsApp Web.")
time.sleep(30)

# Ensure JSON file exists before proceeding
last_saved_data = read_json()

# Ensure today's messages exist before proceeding
check_today_label()

# Start a separate thread for 'q' key listening
stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
stop_thread.start()

while True:  # Keep checking for new messages
    for i in range(1, 101):
        # XPath for time elements
        time_xpath = f'//*[@id="main"]/div[3]/div/div[2]/div[3]/div[{i}]/div/div/div[1]/div[2]/div[1]/div/div[3]/div/span'

        try:
            # Find timestamp
            timestamp_element = driver.find_element(By.XPATH, time_xpath)
            timestamp_text = timestamp_element.text.strip()
            latest_timestamp = timestamp_text  # Store latest timestamp

            # If a timestamp was found, check recency
            if latest_timestamp:
                try:
                    message_time = datetime.strptime(latest_timestamp, "%I:%M %p")  # Convert WhatsApp time
                    current_time = datetime.now()

                    message_minutes = message_time.hour * 60 + message_time.minute
                    current_minutes = current_time.hour * 60 + current_time.minute

                    time_diff = current_minutes - message_minutes

                    # Only update JSON if the message is under 1 minute old
                    if 0 <= time_diff <= 1000:
                        # Try normal message structure first
                        msg_xpaths = [
                            f'//*[@id="main"]/div[3]/div/div[2]/div[3]/div[{i}]/div/div/div[1]/div[2]/div[1]/div/div[2]/div/span[1]/span',  # Normal message
                            f'//*[@id="main"]/div[3]/div/div[2]/div[3]/div[{i}]/div/div/div[1]/div[2]/div[1]/div/div[2]/div[2]/span[1]/span'  # Replied message
                        ]

                        
                        for msg_xpath in msg_xpaths:
                            try:
                                message_element = driver.find_element(By.XPATH, msg_xpath)
                                latest_message_text = message_element.text.strip()

                                # Save message if it's not already stored
                                if latest_message_text not in last_saved_data.get(latest_timestamp, []):
                                    answerable = process_text(latest_message_text)[1]
                                    response = process_text(latest_message_text)[1]
                                    if answerable:
                                        sys.stdout.write(f"\r🔔 New message detected: {latest_message_text} at {latest_timestamp}    ")
                                        write_json(latest_timestamp, latest_message_text)
                                        last_saved_data = read_json()  # Reload JSON data to keep updated

                                        msg_box_Xpath = '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'
                                        msg_box = driver.find_element(By.XPATH, msg_box_Xpath)
                                        msg_box.click()
                                        msg_box.send_keys(response)
                                        msg_box.send_keys(Keys.RETURN)
                                        # Start the alarm if it's not already playing
                                        threading.Thread(target=play_audio, args=("digital-alarm-clock-151920.mp3",), daemon=True).start()
                                else:
                                    sys.stdout.write("\r⚠️ Message already saved, not updating.    ")

                                break  # Exit loop as soon as correct text is found
                            except Exception:
                                continue  # Try the next possible message XPath

                    else:
                        sys.stdout.write(f"\r🕒 Latest message is too old ({time_diff} minutes ago), not updating JSON.    ")

                except ValueError:
                    sys.stdout.write(f"\r❌ Could not parse timestamp format: {latest_timestamp}    ")

        except Exception:
            continue  # Skip if element is missing

    # Ensure immediate output & wait before checking again
    sys.stdout.flush()
    time.sleep(5)