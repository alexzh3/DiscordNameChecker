# DiscordNameChecker
A Python Discord script that is able to check the availability of an username on Discord from a wordlist text file.

# Instructions:
1. Download Python3 https://www.python.org/downloads/
2. Download or clone the repo.
3. Run `pip install -r requirements.txt`, the only package needed is requests
4. Create a `tokens.txt` file which should include a token and a password in the following format `token:password` on every line.
5. Change the `env.txt` variables to your liking, where `tocheck` is the name of the list of usernames to check and `available` a text file which will include the available names.
6. Run `Python namechecker.py`

**Remember to never share your Discord authentication token.**
