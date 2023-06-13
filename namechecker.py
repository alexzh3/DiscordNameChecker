import requests
import time
import threading

def read_variables(filename):
    variables = {}
    with open(filename, "r") as file:
        for line in file:
            name, value = line.strip().split("=")
            variables[name] = value.strip()
    return variables

def handle_taken(data, username):
    print(data)
    print(f'{username} is already taken')

def handle_rate_limited(data, username, url, headers, payload):
    print(data)
    retry_after = data.get('retry_after', 0) + 0.1
    print(f"Rate limited, waiting {retry_after} seconds")
    time.sleep(retry_after)

    response = requests.patch(url, headers=headers, json=payload)
    data = response.json()

    if "code" in data:
        if data.get('code') == 50035:
            handle_taken(data, username)
            return False
        elif data.get('code') == 10020 or 'captcha_key' in data:
            handle_available(data, username)
            return False

    if "retry_after" in data:
        return handle_rate_limited(data, username, url, headers, payload)
    else:
        return handle_unknown(data)

def handle_available(data, username):
    print(data)
    print(f'{username} is available and is added to the text file')
    with open(variables["available"], 'a') as file:
        file.write(str(username) + '\n')

def handle_unknown(data):
    print(data)
    print("Unknown error code, stopped the script")
    return True

def check_username(token, username):
    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "accept": "*/*",
        "authorization": token,
        "content-type": "application/json",
    }
    payload = {
        "username": username
    }
    response = requests.patch(url, headers=headers, json=payload)
    data = response.json()

    if "code" in data:
        if data.get('code') == 50035:
            handle_taken(data, username)
        elif data.get('code') == 10020 or 'captcha_key' in data:
            handle_available(data, username)
        elif "retry_after" in data:
            if handle_rate_limited(data, username, url, headers, payload):
                return
        else:
            if handle_unknown(data):
                return

    time.sleep(2.5)

variables = read_variables("env.txt")
tokens = [line.strip() for line in open("tokens.txt", "r")]

usernames = []
with open(variables["tocheck"], "r") as file:
    for line in file:
        usernames.extend(line.strip().split())

num_threads = len(tokens)

def process_usernames(start, end):
    for i in range(start, end):
        if i >= len(usernames):
            break
        username = usernames[i]
        token = tokens[i]
        check_username(token, username)

threads = []
chunk_size = len(usernames) // num_threads
for i in range(num_threads):
    start = i * chunk_size
    end = start + chunk_size
    thread = threading.Thread(target=process_usernames, args=(start, end))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
