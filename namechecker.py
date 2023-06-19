import requests
import threading
import time
import os
from tqdm import tqdm

# Read the file and extract the variables
with open("env.txt", "r") as file:
    env_data = [line.strip().split("=") for line in file]
    env_dict = dict(env_data)
    tocheck = env_dict.get("tocheck")
    available = env_dict.get("available")
    loop = env_dict.get("loop")
    notifications = env_dict.get("notifications") == "True"
    bot_token = env_dict.get("bot_token")
    chat_id = env_dict.get("chat_id")


# Read the tokens and passwords from the file
with open("tokens.txt", "r") as file:
    tokens, passwords = zip(*(line.strip().split(":") for line in file))

usernames = []
for i in range(int(loop)):
    with open(tocheck, "r") as file:
        for line in file:
            words = line.strip().split()
            usernames.extend(words)

# Process username list for each thread iteratively
def process_usernames(token, password, run_event, progress_bar):
    while run_event.is_set() and usernames:
        username = usernames.pop(0)  # Get and remove the first username from the list
        url = "https://discord.com/api/v9/users/@me"
        headers = {
            "accept": "*/*",
            "authorization": token,
            "content-type": "application/json",
        }
        payload = {
            "username": username,
            "password": password
        }
        response = requests.patch(url, headers=headers, json=payload)
        data = response.json()
        if data.get('code', 0) == 50035:
            handle_taken(data, username)
        elif (data.get('code', 0) == 10020 or 'captcha_key' in data):
            handle_available(data, username)
        elif "retry_after" in data:
            time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
            handle_rate_limited(data, username, url, headers, payload)
        else:
            print(f"Unknown error or 401, token: {token}, pass:{password}")
            handle_unknown(data)

        time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
        progress_bar.update(1)  # Increment progress bar`
        if len(usernames) == 3:
            message = f"Done with checking: {tocheck}"
            send_telegram_message(bot_token, chat_id, message)


def handle_taken(data, username):
    print(data)
    print(f'{username} is already taken')


def handle_rate_limited(data, username, url, headers, payload):
    print(data)
    print(f"Rate limited, waiting {data.get('retry_after') + 0.1} seconds")
    time.sleep(data.get('retry_after') + 0.1)  # Wait for rate limit

    response = requests.patch(url, headers=headers, json=payload)  # try again
    data = response.json()

    if data.get('code', 0) == 50035:
        handle_taken(data, username)
    elif (data.get('code', 0) == 10020 or 'captcha_key' in data):
        handle_available(data, username)
    elif "retry_after" in data:
        handle_rate_limited(data, username, url, headers, payload)
    else:
        handle_unknown(data)


def handle_available(data, username):
    print(data)
    print(f'{username} is available and is added to the text file')
    with open(available, 'a') as file:
        file.write(str(username) + '\n')
    if notifications == True:
        message = f"Username found: {username}"
        send_telegram_message(bot_token, chat_id, message)
        message = username
        send_telegram_message(bot_token, chat_id, message)


def handle_unknown(data):
    print(data)
    os._exit(1)

# Replace with your own Telegram bot token and chat ID
def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, params=params)
    if response.status_code != 200:
        print("Failed to send Telegram message.")


# Create an event object to signal threads
run_event = threading.Event()
run_event.set()

# Number of threads
num_threads = min(len(tokens), len(usernames))

# Create and start the threads
threads = []
with tqdm(total=len(usernames), desc="Checking usernames") as progress_bar:
    for i, (token, password) in enumerate(zip(tokens, passwords)):
        thread = threading.Thread(target=process_usernames, args=(token, password, run_event, progress_bar))
        threads.append(thread)
        thread.start()

    # Wait for keyboard interrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Attempting to close threads")
        run_event.clear()  # Signal threads to stop
        for thread in threads:
            thread.join()  # Wait for threads to finish
        print("Threads successfully closed")
