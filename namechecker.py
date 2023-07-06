import requests
import threading
import time
import os
from tqdm import tqdm
import logging
import datetime
from itertools import cycle
import random


def read_env_file(file_path):
    with open(file_path, "r") as file:
        env_data = [line.strip().split("=") for line in file]
        env_dict = dict(env_data)
        return env_dict


def configure_logging(log_type):
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = f"log_{current_datetime}.txt"
    handlers = [logging.StreamHandler()]  # Always display logs in the terminal

    log_level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level_mapping[log_type] == logging.DEBUG:
        handlers.append(
            logging.FileHandler(log_file)
        )  # Add file handler for DEBUG level

    logging.basicConfig(
        level=log_level_mapping[log_type],
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def create_proxy_pool(proxy_enabled, proxy_token):
    proxies_formatted = []
    if proxy_enabled:
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
    return proxy_pool


# Setup usernames
def read_usernames():
    with open(tocheck, "r") as file:
        for line in file:
            username = line.strip().split()
            usernames.extend(username)


# Read tokens
def read_tokens():
    with open("tokens.txt", "r") as file:
        for line in file:
            line = line.strip()
            token = line
            tokens.append(token)
    return tokens


# Process an username request
def process_usernames(token, run_event, progress_bar, url):
    global hasLock
    try:
        while run_event.is_set() and usernames:
            if url == url_attempt:
                time.sleep(20)  # Sleep 20 seconds
            if len(usernames) == 0:
                if loop:
                    if not hasLock:
                        hasLock =  True
                        with lock:
                            read_usernames()    # Re-populate the usernames list from the tocheck file
                            reset_progress_bar(progress_bar, len(usernames))
                        hasLock = False
                else:
                    time.sleep(30)
                    message = f"Done with checking: {tocheck}"
                    send_telegram_message(bot_token, chat_id, message)
                    os._exit(1)
            try:
                username = usernames.pop(0)
            except Exception as e:
                logging.error(f"Exception occurred while popping username: {str(e)}")
                continue
            if proxy_enabled:
                proxy = next(proxy_pool)
                proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            url = url
            headers = {
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "en-US,en;q=0.9",
                "authorization": token,
                "content-type": "application/json",
                "origin": "https://discord.com",
                "referer": "https://discord.com/channels/@me",
                "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "Windows",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
                "x-debug-options": "bugReporterEnabled",
                "x-super-properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6Im5sLU5MIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExNC4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTE0LjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjIwODMxOSwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbH0",
            }
            payload = {"username": username}
            try:
                response = requests.post(
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
                progress_bar.update(-1)  # Update progress bar
                time.sleep(random.randint(5, 10))
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
                progress_bar.update(-1)  # Update progress bar
                return  # Stop the current thread
            elif "retry_after" in data:
                logging.debug(f"{threading.current_thread().name} - {data}")
                logging.info(
                    f"{threading.current_thread().name} - Rate limited, waiting {data.get('retry_after') + 1} seconds"
                )
                time.sleep(data.get("retry_after") + 1)  # Wait for rate limit
                process_usernames(
                    token, run_event, progress_bar, url_attempt
                )  # Retry with attempt url
            elif data.get("code") == 40001:
                logging.error(f"{threading.current_thread().name} - {data}")
                logging.error(
                    f"Token not verified with phone or mail yet, token: {token}, {threading.current_thread().name}"
                )
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of error
                progress_bar.update(-1)  # Update progress bar
                return  # Stop current thread
            else:
                handle_unknown(data)
            progress_bar.update(1)  # Update progress bar

    except Exception as e:
        logging.exception(
            f"Exception occurred in {threading.current_thread().name}: {str(e)} for token: {token}"
        )
        os._exit(1)


def handle_taken(data, username):
    logging.debug(f" {threading.current_thread().name} - {data}")
    logging.info(f" {threading.current_thread().name} - {username} is already taken")


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
    logging.error(f"Unknown error, token: {token}, {threading.current_thread().name}")
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


# Set config variables
env_dict = read_env_file("env.txt")
tocheck = env_dict.get("tocheck")
available = env_dict.get("available")
loop = env_dict.get("loop") == "True"
notifications = env_dict.get("notifications") == "True"
bot_token = env_dict.get("bot_token")
chat_id = env_dict.get("chat_id")
log_type = env_dict.get("log_type")
proxy_enabled = env_dict.get("proxy_enabled") == "True"
proxy_token = env_dict.get("proxy_token")
configure_logging(log_type)

# Read usernames
usernames = []
read_usernames()

# Read the tokens and passwords from the file
tokens = []
tokens = read_tokens()

# Config Proxies, create proxy pool
proxy_pool = create_proxy_pool(proxy_enabled, proxy_token)

# Create an event object to signal threads
run_event = threading.Event()
run_event.set()

# Number of threads
num_threads = min(len(tokens), len(usernames))

# Create lock and global bool
lock = threading.Lock()
hasLock = False

# URL
url_attempt = "https://discord.com/api/v9/users/@me/pomelo-attempt"

# Username list length
usernames_length = len(usernames)

# Create and start the threads
threads = []
with tqdm(total=usernames_length, desc="Checking usernames") as progress_bar:
    for i, token in enumerate(tokens):
        time.sleep(0.24)  # Don't start all at the same time
        thread_num = i  # Thread number starts from 1
        thread_name = f"Thread-{thread_num}"
        thread = threading.Thread(
            target=process_usernames,
            args=(token, run_event, progress_bar, url_attempt),
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