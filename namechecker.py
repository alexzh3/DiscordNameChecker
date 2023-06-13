import requests
import time

# Read the file and extract the variables
with open("env.txt", "r") as file:
    for line in file:
        # Split each line at the equals sign to separate variable name and value
        name, value = line.strip().split("=")
        # Remove any leading or trailing whitespace from the value
        value = value.strip()
        # Assign the value to the corresponding variable
        if name == "token":
            token = value
        elif name == "tocheck":
            tocheck = value
        elif name == "available":
            available = value

def handle_taken(data, username):
    print(data)
    print(f'{username} is already taken')

def handle_rate_limited(data, username):
    print(data)
    print(f"Rate limited, waiting {data.get('retry_after') + 0.1} seconds")
    time.sleep(data.get('retry_after') + 0.1)  # Wait for rate limit

    response = requests.patch(url, headers=headers, json=payload)  # try again
    data = response.json()

    if "code" in data and data.get('code') == 50035:
        handle_taken(data, username)
        return False
    elif "code" in data and (data.get('code') == 10020 or 'captcha_key' in data):
        handle_available(data, username)
        return False
    elif "retry_after" in data:
        return handle_rate_limited(data, username)
    else:
        return handle_unknown(data)
        
def handle_available(data, username):
    print(data)
    print(f'{username} is available and is added to the text file')
    with open(available, 'a') as file:
        file.write(str(username) + '\n')

def handle_unknown(data):
    print(data)
    print("Unknown error code, stopped the script")
    return True

usernames = []
with open(tocheck, "r") as file:
    for line in file:
        line = line.strip()  # Remove leading/trailing whitespace
        words = line.split()  # Split the line into words
        usernames.extend(words)  # Add the words to the list

for username in usernames:
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
    
    if "code" in data and data.get('code') == 50035:
        handle_taken(data, username)
    elif "code" in data and (data.get('code') == 10020 or 'captcha_key' in data):
        handle_available(data, username)
    elif "retry_after" in data:
        if handle_rate_limited(data, username):
            break  # only break if unknown error
    else:
        if handle_unknown(data):
            break  # only break if unknown error

    time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
