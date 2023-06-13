import requests
import time

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

variables = read_variables("env.txt")
usernames = []
with open(variables["tocheck"], "r") as file:
    for line in file:
        usernames.extend(line.strip().split())

for username in usernames:
    url = "https://discord.com/api/v10/users/@me"
    headers = {
        "accept": "*/*",
        "authorization": variables["token"],
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
                break
        else:
            if handle_unknown(data):
                break

    time.sleep(2.5)
