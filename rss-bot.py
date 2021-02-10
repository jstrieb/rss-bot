#!/usr/bin/python3

import argparse
import cgi
import cgitb
import json
import os
import sys
import time

from hashlib import md5
from typing import Dict

# Required to make feedparser import successfully in Apache cgi-bin
for user in os.listdir("/home"):
    sys.path.insert(0, f"/home/{user}/.local/lib/python3.8/site-packages")

import feedparser

from html2text import html2text

from groupme import GroupmeBot


###############################################################################
# Global variables
###############################################################################

DEBUG = True


###############################################################################
# Helper Functions
###############################################################################

def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments
    :return: parsed arguments as generated by argparse module
    """
    parser = argparse.ArgumentParser(description="Manage RSS feeds.")

    parser.add_argument("-c", "--cron", action="store_true",
                        help="Check feeds instead of handling messages")
    parser.add_argument("-f", "--feed_file", action="store",
                        default="/home/jstrieb/.rssfeeds.json",
                        help="File with stored feed metadata")

    return parser.parse_args()


def load_data(feed_filename: str) -> Dict:
    try:
        with open(feed_filename, "r") as f:
            feeds = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        feeds = dict()
    return feeds


def save_data(feed_filename: str, feed_data: Dict) -> None:
    with open(feed_filename, "w") as f:
        json.dump(feed_data, f, indent=2)


def check_feed(bot: GroupmeBot, feed: Dict, silent: bool = False) -> None:
    feed_data = feedparser.parse(feed.get("feed_url", ""))

    feed["title"] = feed_data.feed.get("title", "No title")
    feed["link"] = feed_data.feed.get("link", "")
    feed["description"] = feed_data.feed.get("description", "")

    # Find new items by using a hash set (literally a hash set of hashes)
    seen = set(feed.get("seen_entries", []))
    entries = dict()
    for entry in feed_data.entries:
        string = entry.get("title", "") + entry.get("summary", "")
        key = md5(string.encode("utf-8")).hexdigest()
        entries[key] = entry

    if not silent:
        for key in set(entries) - seen:
            entry = entries[key]
            output = feed.get("title", "")
            if "title" in entry:
                output += "\n" + entry["title"].strip()
            if "description" in entry and len(entry["description"]) < 500:
                output += "\n" + html2text(entry["description"]).strip()
            if "link" in entry:
                output += "\n" + entry["link"].strip()
            bot.send(output)

    feed["seen_entries"] = list(seen | set(entries))


def check_feeds(bot: GroupmeBot, feed_filename: str,
                silent: bool = False) -> None:
    """
    Check feeds for updates, sending via GroupMe if updated info
    :param bot: bot to send updates with
    :param feed_filename: saved feed data to read from and write to
    :param silent: whether to send updates with the bot or not
    """
    feeds = load_data(feed_filename)
    feeds["feedlist"] = feeds.get("feedlist", [])

    for feed in feeds["feedlist"]:
        check_feed(bot, feed, silent=silent)

    feeds["last_checked"] = int(time.time())
    save_data(feed_filename, feeds)


def handle_post(bot: GroupmeBot, data: Dict,
                headers: Dict[str, str], feed_filename: str) -> None:
    """
    Handle user commands sent via GroupMe and received over CGI
    :param bot: bot to send replies with
    :param data: GroupMe message data
    :param headers: HTTP headers
    :param feed_filename: saved feed data to read from and write to
    """
    # Don't respond to other bots
    if data.get("sender_type", None) == bot:
        return

    text = data.get("text", "").lower().strip()

    if text == "help":
        bot.send("Usage: rsssub <rss url>\n"
                 "       rssunsub <number>\n"
                 "       rssinfo <number>\n"
                 "       rsslist")

    elif text.startswith("rsssub") or text.startswith("rssub"):
        params = data.get("text", "").strip().split()[1:]
        if len(params) < 1:
            bot.send("Usage: rsssub <rss url>")
            return

        url = params[0]
        feed_data = load_data(feed_filename)
        feed_data["feedlist"] = feed_data.get("feedlist", []) + [{
            "feed_url": url,
        }]
        save_data(feed_filename, feed_data)
        bot.send(f"Added feed \"{url}\"")

        check_feeds(bot, feed_filename, silent=True)

    elif text.startswith("rssunsub"):
        params = text.split()[1:]
        if len(params) < 1:
            bot.send("Usage: rssunsub <number>")
            return

        feed_index = int(params[0]) - 1
        feed_data = load_data(feed_filename)
        if not (0 <= feed_index < len(feed_data["feedlist"])):
            bot.send("Feed number out of bounds!")
            return

        feed = feed_data["feedlist"][feed_index]
        del feed_data["feedlist"][feed_index]
        save_data(feed_filename, feed_data)

        bot.send(f"Unsubscribed \"{feed.get('tite', '')}\"\n"
                 f"{feed.get('feed_url', '')}")

    elif text.startswith("rssinfo"):
        params = text.split()[1:]
        if len(params) < 1:
            bot.send("Usage: rssinfo <number>")
            feeds = load_data(feed_filename).get("feedlist", [])
            titles = map(lambda f: f"{f[0] + 1}. {f[1].get('title', '')}",
                         enumerate(feeds))
            bot.send("Subscribed feeds:\n" + "\n".join(titles))
            return

        feed_index = int(params[0]) - 1
        feeds = load_data(feed_filename).get("feedlist", [])
        if not (0 <= feed_index < len(feeds)):
            bot.send("Feed number out of bounds!")
            return

        feed = feeds[feed_index]
        bot.send(f"Title: {feed.get('title', '')}\n"
                 f"Description: {feed.get('description', '')}\n"
                 f"Link: {feed.get('link', '')}")

    elif text.startswith("rsslist"):
        feeds = load_data(feed_filename).get("feedlist", [])
        titles = map(lambda f: f"{f[0] + 1}. {f[1].get('title', '')}",
                     enumerate(feeds))
        bot.send("Subscribed feeds:\n" + "\n".join(titles))


###############################################################################
# Main function
###############################################################################

def main(bot_id: str) -> None:
    env = dict(os.environ)
    args = parse_args()
    if bot_id is None:
        raise Exception("No bot ID supplied! Missing RSS_BOT_ID env variable.")
    bot = GroupmeBot(bot_id=bot_id)

    try:
        if args.cron or "REQUEST_METHOD" not in env:
            check_feeds(bot, args.feed_file)
        elif env.get("REQUEST_METHOD").lower() == "post":
            print("Content-type: text/html\n\n")

            headers = {k[5:].replace("_", "-"): v for k, v in env.items()
                       if k.startswith("HTTP_")}
            content_length = int(env.get("CONTENT_LENGTH", 0))
            data = json.loads(sys.stdin.read(content_length))
            handle_post(bot, data, headers, args.feed_file)
        else:
            assert(env.get("REQUEST_METHOD").lower() == "get")
            print("Content-type: text/html\n\n")
            print("Nothing to see here.")
    except Exception as e:
        if DEBUG:
            raise e
        else:
            bot.send(f"Exception\n{str(e)}")


if __name__ == "__main__":
    # NOTE: RSS_BOT_ID environment variable must bet set in two places to work
    # with Apache:
    # - Add "export RSS_BOT_ID=..." to /etc/apache2/envvars
    # - Add "SetEnv RSS_BOT_ID ${RSS_BOT_ID}" to VirtualHost in
    #   /etc/apache2/sites-available/000-default.conf

    # Make sure to also run
    # touch ~/.rssfeeds.json
    # chmod 666 .rssfeeds.json

    if DEBUG:
        # Display errors in a well-formatted way if debugging
        print("Content-type: text/html\n\n")
        cgitb.enable()
        main(os.getenv("RSS_BOT_ID", None))
    else:
        try:
            main(os.getenv("RSS_BOT_ID", None))
        # Catch all exceptions so we don't leak errors and cause security vulns
        except:
            print(e)
