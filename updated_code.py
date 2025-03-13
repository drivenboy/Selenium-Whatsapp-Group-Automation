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
JSON_FILE = "latest_messages.json"

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
    global time0
    try:
        # Find all "TODAY"/"HEUTE" label elements
        today_label_container = driver.find_element(By.XPATH, '//div[@class="_amk4 _amkb"]/span[contains(text(), "HEUTE") or contains(text(), "TODAY")]')
        time0 =time.time()
        # print(f"Time taken to get today's messages: {time0-start_time} seconds")  # mEasuring latency
        # print(f"Time taken so far: {time0-start_time} seconds")  # measuring latency
        # Move to its parent and get all *next* sibling elements that contain messages
        today_container = today_label_container.find_element(By.XPATH, "./../..")
        
        # Find all messages appearing after the 'TODAY' label (Incoming & Outgoing)
        chat_containers = today_container.find_elements(By.XPATH, './following-sibling::div[@role="row"]')

        return chat_containers  # Return only messages appearing after "TODAY"

    except Exception as e:
        print(f"⚠️ Error finding 'TODAY' section: {e}")
        time0 =time.time()
        # print(f"Time taken to get today's messages: {time0-start_time} seconds")  # mEasuring latency
        # print(f"Time taken so far: {time0-start_time} seconds")  # measuring latency
        return []  # Return empty list if "TODAY" isn't found


def get_visible_chat(driver):
    chat_containers = get_today_messages(driver)  # Get only today's messages
    chat_containers.reverse()
    time1 =time.time()
    # print(f"Time taken to get today's messages: {time1-time0} seconds")  # mEasuring latency
    # print(f"Time taken so far: {time1-start_time} seconds")  # measuring latency

    if not chat_containers:  # Ensure we're checking only today's messages
        sys.stdout.write("\r⚠️ No messages found NOW. Waiting for new messages...")
        sys.stdout.flush()
        time1 =time.time()
        # print(f"Time taken to get today's messages: {time1-time0} seconds")  # mEasuring latency
        # print(f"Time taken so far: {time1-start_time} seconds")  # measuring latency
        return None, None

    latest_time_diff = float("inf")

    latest_timestamp = None

    latest_messagess = ""

    for id,chat in enumerate(chat_containers) if chat_containers else []:
        # print(f"✅ Extracting {id+1} of {len(chat_containers)} messages from 'TODAY' section.")  # Debugging output
        time2 =time.time()
        # print(f"Time taken to extract message container-{id+1}: {time2-time1} seconds")  # measuring latency
        # print(f"Time taken so far: {time2-start_time} seconds")  # measuring latency
        try:
            
            # Extract timestamps from sibling elements
            timestamp_elements = chat.find_elements(By.XPATH, './/span[@class="x1rg5ohu x16dsc37"]')
            timestamp_text = timestamp_elements[-1].text.strip() if timestamp_elements else None  # Pick the last timestamp
            if timestamp_text:
                timestamp_text = timestamp_text.replace("Edited", "") if "Edited" in timestamp_text else timestamp_text
            # print("Extracted Timestamp:", timestamp_text)  # Debugging output

            # Convert timestamp to datetime
            if timestamp_text:
                message_time = datetime.strptime(timestamp_text, "%I:%M %p")
                current_time = datetime.now()
                time_diff = abs((current_time.hour * 60 + current_time.minute) - (message_time.hour * 60 + message_time.minute))

                # if time_diff < latest_time_diff:
                #     latest_time_diff = time_diff
                #     print(f"Latest Time Difference: {latest_time_diff} min")  # Debugging output
                #     print(f"Latest Message: {message_text}")  # Debugging output
                
                # Check if this is the most recent message within 1 minute
                if time_diff <= 1 and time_diff <= latest_time_diff:
                    # Extract **all spans** inside the message container (Handles multi-line messages)
                    message_elements = chat.find_elements(By.XPATH, './/div[@class="_akbu"]/span')
                    message_text = "\n".join([span.text.strip() for span in message_elements if span.text.strip()])  # Join spans with newline

                    latest_time_diff = time_diff
                    
                    if message_text:
                        print("Extracted Message:", message_text)  # Debugging output

                        schichts = ('spätschicht', 'frühschicht', 'nachtschicht')
                        message_text = message_text.lower()


                        for schicht in schichts:
                            if any((all(l in message_text for l in ('mitarbeiter', 'benötigen', schicht)), 
                                    all(s1 in message_text for s1 in ('wer kann', schicht)), 
                                    all(s2 in message_text for s2 in ('kann', 'jemand', schicht)),
                                    all(s3 in message_text for s3 in ('person', schicht)))):
                                    latest_messagess += message_text
                    
                    latest_timestamp = timestamp_text

                else:
                    break

        except Exception as e:
            print(f"⚠️ Error extracting message or timestamp: {e}")
            continue  # Skip any errors and move to the next message

    global time3
    time3 =time.time()
    print(f"Time taken to scan all messages: {time3-time2} seconds")  # measuring latency
    print(f"Time taken so far: {time3-start_time} seconds")  # measuring latency

    return latest_timestamp, latest_messagess


# Function to process message text (modify based on logic)
def process_text(msg_text):
    schichts = ('spätschicht', 'frühschicht', 'nachtschicht')
    tage = ('jetzt', 'heute', 'morgen', 'samstag', 'sonntag', 'montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag')
    msg_text = msg_text.lower()
    ans = False
    s = []
    t = []
    simple_mode = False


        # if any((all(l in msg_text for l in ('mitarbeiter', 'benötigen', schicht)), 
        #         all(s1 in msg_text for s1 in ('wer kann', schicht)), 
        #         all(s2 in msg_text for s2 in ('kann', 'jemand', schicht)),
        #         all(s3 in msg_text for s3 in ('person', schicht)))):

    if not simple_mode:
        for tag in tage:
            if tag in msg_text and tag.capitalize() not in t:
                tag = tag.capitalize() if all((tag != 'jetzt', tag != 'heute')) else tag
                t.append(tag)

        for schicht in schichts:
            if schicht in msg_text and schicht not in s:
                schicht = schicht.capitalize()
                s.append(schicht)
                ans = True

    if ans:
        msg = 'Ich kann jeden Tag Frühschicht oder Spätschicht arbeiten.' if simple_mode else 'Ich kann {} {} arbeiten.'.format(', '.join(t), ' oder '.join(s))
        return ans, msg

    return ans, " "

def answer(response):
    msg_box = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/footer/div[1]/div/span/div/div[2]/div[1]/div[2]/div[1]/p'))
                    )
    # response = str(response) + "execution_time: "+ str(time5-start_time)+" sec"
    msg_box.send_keys(response)
    msg_box.send_keys(Keys.RETURN)

    time5 =time.time()
    print(f"Time taken to send message: {time5-time4} seconds")  # measuring latency
    print(f"Total time taken: {time5-start_time} seconds")  # measuring latency


audio_playing = False
audio_lock = threading.Lock()


def play_audio(audio_file):
    """Continuously plays the alarm every 15 seconds until 'q' is pressed."""
    global audio_playing
    pg.mixer.init()
    pg.mixer.music.load(audio_file)

    with audio_lock:
        if audio_playing:  # Prevent multiple alarms from playing
            return
        audio_playing = True

    try:
        while audio_playing:  # Loop until 'q' is pressed
            pg.mixer.music.play()
            sys.stdout.write("\r🔊 Alarm playing... Press 'q' to stop.  ")
            sys.stdout.flush()

            # Instead of sleeping 15s, break into 1s chunks and check every second
            for _ in range(15):  
                if not audio_playing:  # If 'q' was pressed, stop immediately
                    break
                time.sleep(1)  # Sleep 1 second before checking again

            # If 'q' was pressed, break the main loop immediately
            if not audio_playing:
                break

    finally:
        stop_audio()  # Ensure the audio stops when loop exits

def stop_audio():
    """Stops the alarm sound immediately."""
    global audio_playing
    with audio_lock:
        audio_playing = False
    pg.mixer.music.stop()  # Force stop the alarm immediately
    print("\n🔕 Audio stopped.")

def listen_for_stop():
    """Listens for the 'q' key to stop the audio."""
    print("Press 'q' to stop the audio.")
    kb.wait('q')  # Waits for 'q' key press
    stop_audio()  # Stop audio immediately

# message_lock = threading.Lock()
# extract_thread = threading.Thread(target=extract_today_messages, daemon=True)
# process_thread = threading.Thread(target=process_latest_messages, daemon=True)
# answer_thread = threading.Thread(target=answer, args=response, daemon=True)

# Continuously monitor for new messages

while True:
    
    start_time = time.time()
    latest_timestamp, latest_messages = get_visible_chat(driver)


    if latest_timestamp and latest_messages:
        last_saved_data = read_json()

        # Print the most recent message **EVERY iteration**
        sys.stdout.write(f"\r⏳ Latest messages in viewport: '{latest_messages}' at {latest_timestamp}   ")
        sys.stdout.flush()

        # Process and respond only if it's a new message
        if latest_messages not in last_saved_data.get(latest_timestamp, []):
            answerable, response = process_text(latest_messages) 
            time4 =time.time()
            print(f"Time taken to process the last message: {time4-time3} seconds")  # measuring latency
            print(f"Time taken so far: {time4-start_time} seconds")  # measuring latency
            
            if answerable:
                sys.stdout.write(f"\r🔔 New message detected: '{latest_messages}' at {latest_timestamp}   ")
                sys.stdout.flush()
                write_json(latest_timestamp, latest_messages)

                try:
                    answer(response)

                    # Start the alarm if it's not already playing
                    if not audio_playing:
                        play_audio_thread = threading.Thread(target=play_audio, args=("digital-alarm-clock-151920.mp3",), daemon=True)
                        play_audio_thread.start()
                        # Start a separate thread for 'q' key listening
                        stop_thread = threading.Thread(target=listen_for_stop, daemon=True)
                        stop_thread.start()
                except:
                    time5 =time.time()
                    # print(f"Time taken to send message: {time5-time4} seconds")  # measuring latency
                    # print(f"Total time taken: {time5-start_time} seconds")  # measuring latency
                    pass