# DiscordNameChecker
A Python Discord script that can check the availability of a username on Discord from a Wordlist text file. 

This tool supports:

- Captcha solving
- Sniping names
- Multi-threading tokens
- Proxies support from Webshare

This tool is not maintained anymore and does not work correctly anymore.

# Instructions:
1. Download Python3 https://www.python.org/downloads/
2. Download or clone the repo.
3. Run `pip install -r requirements.txt`, the only package needed is requests
4. Create a `tokens.txt` file which should include a token and a password in the following format `token:password` on every line.
5. Change the `env.txt` variables to your liking, where `tocheck` is the name of the list of usernames to check and `available` a text file which will include the available names.
6. Run `Python namechecker.py`

**Remember to keep your Discord authentication token private. The usage of this tool is educational. I am not responsible for your usage of this tool and its effects on your account.**
