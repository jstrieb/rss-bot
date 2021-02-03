# RSS GroupMe Chatbot

This code implements a simple RSS feed inside of a group chat. Users in the
chat can submit RSS feeds. If the script is run regularly (e.g. via `cron`),
then it will also send updates when any of the feeds are updated.

# Quick Start

Clone the program into your `cgi-bin` directory.

```
cd /usr/lib/cgi-bin/
git clone git@github.com:jstrieb/rss-bot.git
cd rss-bot
```

Install requirements by running the following. If Apache gives errors about
modules not being found, or it's mysteriously not working, try running the
command as `sudo` instead.

```
python3 -m pip install --upgrade --requirement requirements.txt
```

[Get a GroupMe bot ID](https://dev.groupme.com/bots/new) and export it. When
doing this, be sure to set the callback URL to
`http://<your_server>/cgi-bin/rss-bot/rss-bot.py`.

```
echo 'export RSS_BOT_ID="YOUR GROUPME BOT ID HERE"' >> ~/.bashrc
```

Also export the bot ID to allow `cron` to see it.

```
echo 'RSS_BOT_ID="YOUR GROUPME BOT ID HERE"' | sudo tee -a /etc/environment
```

Make sure Apache has access to the `RSS_BOT_ID` environment variable.

- Add `export RSS_BOT_ID` to `/etc/apache2/envvars`
- Add `SetEnv RSS_BOT_ID ${RSS_BOT_ID}` to `VirtualHost` in
  `/etc/apache2/sites-available/000-default.conf`

Allow the `cgi-bin` script permission to look at your stored data file.

```
touch ~/.rssfeeds.json
chmod 666 .rssfeeds.json
```

Add the program to the `crontab` by running `crontab -e` and adding an entry
like the following.

```
*/5 * * * * python3 /usr/lib/cgi-bin/rss-bot/rss-bot.py
```

Restart Apache.

```
sudo service apache2 restart
```

# Project Status

This was a one-off project that I use personally, and may improve. It is not
meant to be supported for public use. As a result, it is unlikely that I will
be particularly responsive to issues or pull requests. Don't hesitate to make
them – just don't expect a snappy response.
