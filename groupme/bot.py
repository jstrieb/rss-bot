#!/usr/bin/python3

# bot.py

import json
import time
from dataclasses import dataclass
from typing import Optional

import requests


################################################################################
# Classes
################################################################################

@dataclass
class GroupmeBot(object):
    """
    Represents a GroupMe bot that can handle sending and receiving messages.
    """
    bot_id: str

    POST_URL = "https://api.groupme.com/v3/bots/post"
    MAX_MSG_LEN = 998

    def send(self, msg: Optional[str]) -> None:
        """
        Send a message from the bot in the group.
        :param msg: Message to send; cuts into substrings of length 998
        """
        if msg is None: return

        for substr in [msg[i:(i + GroupmeBot.MAX_MSG_LEN)] for i in
                       range(0, len(msg), GroupmeBot.MAX_MSG_LEN)]:
            data = {
                "bot_id": self.bot_id,
                "text": substr,
            }
            requests.post(GroupmeBot.POST_URL, json=data)
            time.sleep(0.5)


################################################################################
# Main Function
################################################################################

def main():
    pass


if __name__ == "__main__":
    main()
