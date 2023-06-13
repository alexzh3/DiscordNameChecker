import requests
import threading
import time
import os

# Read the file and extract the variables
with open("env.txt", "r") as file:
    env_data = [line.strip().split("=") for line in file]
    env_dict = dict(env_data)
    tocheck = env_dict.get("tocheck")
    available = env_dict.get("available")

# Read the tokens and passwords from the file
with open("tokens.txt", "r") as file:
    tokens, passwords = zip(*(line.strip().split(":") for line in file))

# Read the usernames from the file
with open(tocheck, "r") as file:
    usernames = [word for line in file for word in line.strip().split()]


# Split username list for each thread to process
def process_usernames(start, end, token, password, run_event):
    for i in range(start, end):
        if i >= len(usernames):
            break
        username = usernames[i]
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
        # Check if the thread should stop
        if not run_event.is_set():
            break
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

def handle_unknown(data):
    print(data)
    os._exit(1)

# Create an event object to signal threads
run_event = threading.Event()
run_event.set()

# Number of threads
num_threads = min(len(tokens), len(usernames))

# Create and start the threads
threads = []
chunk_size = len(usernames) // num_threads
for i, (token, password) in enumerate(zip(tokens, passwords)):
    start = i * chunk_size
    end = start + chunk_size + (1 if i < len(usernames) % num_threads else 0)
    thread = threading.Thread(target=process_usernames, args=(start, end, token, password, run_event))
    threads.append(thread)
    thread.start()

# Wait for keyboard interrupt
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Attempting to close threads")
    run_event.clear() # Signal threads to stop
    for thread in threads:
        thread.join() # Wait for threads to finish
    print("Threads successfully closed")