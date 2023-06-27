import requests
import threading
import time
import os
from tqdm import tqdm
import logging
import datetime
from itertools import cycle

# Read the file and extract the variables
with open("env.txt", "r") as file:
    env_data = [line.strip().split("=") for line in file]
    env_dict = dict(env_data)
    tocheck = env_dict.get("tocheck")
    available = env_dict.get("available")
    loop = env_dict.get("loop") == "True"
    notifications = env_dict.get("notifications") == "True"
    bot_token = env_dict.get("bot_token")
    chat_id = env_dict.get("chat_id")
    log_type = env_dict.get("log_type")
    proxy_enabled = env_dict.get("proxy_enabled") == "True"
    proxy_token = env_dict.get("proxy_token")


# Configure loggingF
current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = f"log_{current_datetime}.txt"

handlers = [logging.StreamHandler()]  # Always display logs in the terminal

# Map log type string to corresponding log level constant
log_level_mapping = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

if log_level_mapping[log_type] == logging.DEBUG:
    handlers.append(logging.FileHandler(log_file))  # Add file handler for DEBUG level

logging.basicConfig(
    level=log_level_mapping[log_type],
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

# Set the log level for the 'requests' and 'urllib3' library to a higher level than application's log level
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# Setup usernames
def read_usernames():
    with open(tocheck, "r") as file:
        for line in file:
            words = line.strip().split()
            usernames.extend(words)


# Read tokens:password
def read_tokens():
    with open("tokens.txt", "r") as file:
        for line in file:
            line = line.strip()
            if ":" in line:
                token, password = line.split(":")
            else:
                token = line
                password = ""  # Empty string
            tokens.append(token)
            passwords.append(password)
    return tokens, passwords


# Process an username request
def process_usernames(token, password, run_event, progress_bar):
    try:
        while run_event.is_set() and usernames:
            if len(usernames) == 1:
                if loop:
                    # Re-populate the usernames list from the tocheck file
                    read_usernames()
                    reset_progress_bar(progress_bar, len(usernames))
                else:
                    time.sleep(6)  # Wait for threads to finish
                    message = f"Done with checking: {tocheck}"
                    send_telegram_message(bot_token, chat_id, message)
                    os._exit(1)

            username = usernames.pop(0)
            if proxy_enabled is True:
                proxy = next(proxy_pool)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            url = "https://discord.com/api/v9/users/@me"
            headers = {
                "accept": "*/*",
                "authorization": token,
                "content-type": "application/json",
            }
            payload = {"username": username, "password": password}
            try:
                if not password:
                    url = "https://discord.com/api/v9/users/@me/pomelo-attempt"
                    payload.pop("password")
                    response = requests.post(
                        url, headers=headers, json=payload, proxies=proxies, timeout=10
                    )
                    data = response.json()
                elif password:
                    response = requests.patch(
                        url, headers=headers, json=payload, proxies=proxies, timeout=10
                    )
                    data = response.json()
            except requests.exceptions.RequestException as e:
                logging.error(
                    f"Request exception occurred in {threading.current_thread().name}: {str(e)}"
                )
                logging.error(f"Proxy exception occurred for proxy: {proxy}")
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of exception
                continue

            if (
                data.get("code") == 50035
                or data.get("username") == username
                or data.get("taken") == True
            ):
                handle_taken(data, username)
            elif (
                data.get("code") == 10020
                or "captcha_key" in data
                or data.get("taken") == False
            ):
                handle_available(data, username)
            elif data.get("code") == 40002:
                handle_verify(data, token)
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of error
                return  # Stop the current thread
            elif "retry_after" in data:
                time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
                handle_rate_limited(data, username, url, headers, payload, proxies)
            else:
                logging.error(
                    f"Unknown error or 401, token: {token}, password:{password}, {threading.current_thread().name}"
                )
                handle_unknown(data)
            time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
            progress_bar.update(1)  # Increment progress bar
    except Exception as e:
        logging.exception(
            f"Exception occurred in {threading.current_thread().name}: {str(e)}"
        )
        os._exit(1)


def handle_taken(data, username):
    logging.debug(f" {threading.current_thread().name} - {data}")
    logging.info(f" {threading.current_thread().name} - {username} is already taken")


def handle_rate_limited(data, username, url, headers, payload, proxies):
    logging.debug(f"{threading.current_thread().name} - {data}")
    logging.info(
        f"{threading.current_thread().name} - Rate limited, waiting {data.get('retry_after') + 0.1} seconds"
    )
    time.sleep(data.get("retry_after") + 0.1)  # Wait for rate limit

    try:
        response = requests.patch(
            url, headers=headers, json=payload, proxies=proxies, timeout=10
        )
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Request exception occurred in {threading.current_thread().name}: {str(e)}"
        )
        logging.error(f"Proxy exception occurred for proxy: {proxy}")

    if data.get("code") == 50035:
        handle_taken(data, username)
    elif data.get("code") == 10020 or "captcha_key" in data:
        handle_available(data, username)
    elif "retry_after" in data:
        handle_rate_limited(data, username, url, headers, payload)
    else:
        handle_unknown(data)


def handle_available(data, username):
    logging.debug(f"{threading.current_thread().name} - {data}")
    logging.info(
        f"{threading.current_thread().name} - {username} is available and is added to the text file"
    )
    with open(available, "a") as file:
        file.write(str(username) + "\n")
    if notifications == True:
        message = f"Username found: {username}"
        send_telegram_message(bot_token, chat_id, message)
        message = username
        send_telegram_message(bot_token, chat_id, message)


def handle_verify(data, token):
    logging.debug(f" {threading.current_thread().name} - {data}")
    logging.info(f" {threading.current_thread().name} - {token} needs to be verified")
    message = f"{token} needs to be verified"
    send_telegram_message(bot_token, chat_id, message)


def handle_unknown(data):
    logging.error(f"{threading.current_thread().name} - {data}")
    os._exit(1)


# Replace with your own Telegram bot token and chat ID
def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    response = requests.post(url, params=params)
    if response.status_code != 200:
        logging.error("Failed to send Telegram message.")


def reset_progress_bar(progress_bar, total):
    progress_bar.total = total
    progress_bar.reset()


# Read usernames
usernames = []
read_usernames()

# Read the tokens and passwords from the file
tokens = []
passwords = []
tokens, passwords = read_tokens()

# Config Proxies
proxies_formatted = []
if proxy_enabled is True:
    # Retrieve list of proxies from API
    response = requests.get(
        f"https://proxy.webshare.io/api/v2/proxy/list/download/{proxy_token}/-/any/username/direct/-/"
    )
    proxy_list = response.text.splitlines()
    # Modify the format of proxies
    for proxy in proxy_list:
        ip, port, username, password = proxy.split(":")
        proxy_formatted = f"{username}:{password}@{ip}:{port}"
        proxies_formatted.append(proxy_formatted)
# Set iterator
proxy_pool = cycle(proxies_formatted)

# Create an event object to signal threads
run_event = threading.Event()
run_event.set()

# Number of threads
num_threads = min(len(tokens), len(usernames))

# Create and start the threads
threads = []
with tqdm(total=len(usernames), desc="Checking usernames") as progress_bar:
    for i, (token, password) in enumerate(zip(tokens, passwords)):
        thread_num = i + 1  # Thread number starts from 1
        thread_name = f"Thread-{thread_num}"
        thread = threading.Thread(
            target=process_usernames,
            args=(token, password, run_event, progress_bar),
            name=thread_name,
        )
        threads.append(thread)
        thread.start()

    # Wait for keyboard interrupt
    try:
        while True:
            time.sleep(0.01)
    except KeyboardInterrupt:
        logging.info("Attempting to close threads")
        run_event.clear()  # Signal threads to stop
        for thread in threads:
            thread.join()  # Wait for threads to finish
        logging.info("Threads successfully closed")
