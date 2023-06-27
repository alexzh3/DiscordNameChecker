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


# Configure logging
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
            payload = {"username": username, "password": password}
            try:
                if not password:
                    url = "https://discord.com/api/v9/users/@me/pomelo"
                    payload.pop("password")
                    response = requests.post(
                        url, headers=headers, json=payload, proxies=proxies, timeout=10
                    )
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

            if data.get("code") == 50035 or data.get("username") == username:
                handle_taken(data, username)
            elif data.get("code") == 10020 or "captcha_key" in data:
                handle_available(data, username)
            elif data.get("code") == 40002:
                handle_verify(data, token)
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of error
                return  # Stop the current thread
            elif "retry_after" in data:
                logging.debug(f"{threading.current_thread().name} - {data}")
                logging.info(
                    f"{threading.current_thread().name} - Rate limited, waiting {data.get('retry_after') + 1} seconds"
                )
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of rate limit
                time.sleep(data.get("retry_after") + 1)  # Wait for rate limit
                process_usernames(token, password, run_event, progress_bar)  # Retry
            elif data.get("code") == 40001:
                logging.error(f"{threading.current_thread().name} - {data}")
                logging.error(
                    f"Token not verified with phone or mail yet, token: {token}, password:{password}, {threading.current_thread().name}"
                )
                usernames.append(
                    username
                )  # Append current username back to list that was not checked because of error
                return  # Stop current thread
            else:
                handle_unknown(data)
            time.sleep(2.5)  # Sleep 2.5 seconds to avoid rate limit
            progress_bar.update(1)  # Increment progress bar
    except Exception as e:
        logging.exception(
            f"Exception occurred in {threading.current_thread().name}: {str(e)} for token: {token}, password:{password}"
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
    logging.error(
        f"Unknown error, token: {token}, password:{password}, {threading.current_thread().name}"
    )
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
