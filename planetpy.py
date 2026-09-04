from telegram import Update
from telegram.ext import ContextTypes
import random
import datetime as dt
import xml.etree.ElementTree as cElementTree
import requests
import time 
import os
import sqlite3

DATA_DIR = os.environ.get("DATA_DIR", ".")

# Where the DataBase file lives
DB_PATH = os.path.join(DATA_DIR, "subscribers.db")

cache = {"data": None, "timestamp": 0} # cache dictionary to store the latest blog posts 
# and the timestamp of when they were fetched

# Creates and returns a connection with its configuration 
def get_connection():
    conn = sqlite3.connect(DB_PATH) # Opens database file/Creates it if it doesn't exist
    conn.row_factory = sqlite3.Row # To access fields by name
    return conn # Return connection

# Creates the table if it doesn't already exist
def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            chat_id TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL
        )
    """)
    conn.commit() # To prevent Table from disappearing after coneection is closed
    conn.close()

# Gets and returns subscribtion details of subscirber with given chat ID
def get_subscriber(chat_id):
    conn = get_connection()
    row = conn.execute(
        # Parameterized Query to prevent SQL injection 
        "SELECT count, hour, minute FROM subscribers WHERE chat_id=?",
        (chat_id,) # Comma is to show its a tuple if only one element present
    ).fetchone() # Fethches one row (first row it finds) or returns None
    conn.close()
    return row
# Adds/Replaces subscriber details into DB 
def add_subscriber(chat_id, count, hour=16, minute=0):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO subscribers (chat_id, count, hour, minute) VALUES (?, ?, ?, ?)",
        (chat_id, count, hour, minute)
    )
    conn.commit()
    conn.close()

# Updates the new time set by subscriber with given chat ID
def update_time(chat_id, hour, minute):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE subscribers SET hour = ?, minute = ? WHERE chat_id = ?",
        (hour, minute, chat_id)
    )
    conn.commit()
    changed = cursor.rowcount # How many rows the statement affected
    conn.close()
    return changed > 0

# Deletes subscirber with given chat ID
def remove_subscriber(chat_id):
    conn = get_connection()
    conn.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()

# Gets all subscribers due to be sent the daily post at given hour and minute
def get_due_subscribers(hour, minute):
    conn = get_connection()
    rows = conn.execute(
        "SELECT chat_id, count FROM subscribers WHERE hour = ? AND minute = ?",
        (hour, minute)
    ).fetchall() # gets all rows 
    conn.close()
    return rows

# Parses first 10 items from http://planetpython.org/rss20.xml and returns a list of 
# dictionaries with the title, link, and description of each item.
def parse_planetpy_rss(number : int):
    now = time.time()
    if cache["data"] is not None and (now - cache["timestamp"]) < 300:
        return cache["data"][:number]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get("https://planetpython.org/rss20.xml", headers=headers) # GET request to download the 
        # RSS feed from the specified URL
    except requests.exceptions.RequestException:
        print("Couldn't reach Planet Python")
        return []
    except cElementTree.ParseError:
        print("Couldn't parse it as XML")
        return []
    parsed_xml = cElementTree.fromstring(response.content)# response.content contains the raw 
    #XML data from the RSS feed and fromstring() parses the XML data into an ElementTree object
    items = []
    for node in parsed_xml.iter():# iter() walks through all the nodes in the XML tree
        if node.tag == "item":# RSS feeds structure each blog post as an <item>
            item = {}
            for item_node in list(node): # look at tags inside <item> tag
                if item_node.tag == "title": 
                    item["title"] = item_node.text
                if item_node.tag == "link":
                    item["link"] = item_node.text
                    #EX:{'title': 'Some Blog Post Title', 'link': 'https://example.com/post'}
            items.append(item)
    cache["data"] = items # stores number of the latest blog posts
    cache["timestamp"] = now
    return cache["data"][:number]# returns the cached data of blog posts

# runs when any other command is sent to the bot to log the command, the chat id of the user,
#  and the time of the command to bot.log
def log_command(func):
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        with open(os.path.join(DATA_DIR, "bot.log"), "a") as f:
            f.write(f"{chat_id} - {func.__name__} - {dt.datetime.now()}\n")
        return await func(update, context)
    return wrapper   

# runs when someone send /start command to the bot, update is info about incoming message and
# context is extra tools and info, "starts the bot and sends a welcome message to the user"
@log_command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send /help to see all the user available commands.")
    # update contains info about incoming message, and bot replies back

# runs when someone send /feed command to the bot, "gets 10 latest blog posts from planetpython.org"
@log_command
async def feed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) > 0:
        if context.args[0].isdigit():
            number = int(context.args[0])
            if number <= 0:
                await update.message.reply_text("Please provide a valid positive number between 0-10")
                return
            elif number > 10:
                await update.message.reply_text("Please provide a valid number between 0-10")
                return
        else:
            await update.message.reply_text("Please provide a valid number after /feed command")
            return
    else:
        number = 10
    posts = parse_planetpy_rss(number) # list of 10 dictionaries
    if not posts:
        await update.message.reply_text("Couldn't reach latest Planet Python blog posts. Please try again later.")
        return
    message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in posts]) # COMPACT LOOP to 
    # create a string with the titles and links of the latest blog posts
    await update.message.reply_text(message) # sends combined message back to the user 
    # with the titles and links of the latest blog posts

# shows current available commands
@log_command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("These are the user available commands:\n\n"
    "/start: starts the bot and shows a welcome message.\n\n"
    "/help: shows this list of available commands and how to use them.\n\n"
    "/feed x: this sends you the x latest blog posts from Planet Python (1-10). If no number is provided, it defaults to 10.\n\n"
    "/random: this sends you a single random blog post from the 10 latest Planet Python posts.\n\n"
    "/search keywords: this searches for blog posts with the provided keywords in the title and sends back any matches.\n\n"
    "/count: this tells you how many blog posts are currently available from Planet Python.\n\n"
    "/author name: this searches for blog posts by the provided author name and sends back any matches.\n\n"
    "/subscribe x: this subscribes you to a daily digest of blog posts, sent at your own chosen time. You'll receive x posts per digest (1-10), or 10 if no number is provided. Defaults to 16:00 UTC until you set your own time.\n\n"
    "/settime hour minute: this allows users that are already subscribed to the daily blog posts to change their blog posts set time.\n\n"
    "/unsubscribe: this unsubscribes you from the daily digest of blog posts.\n\n"
    "/mysettings: this shows your current subscription status, your post count, and your chosen digest time.\n\n"
    )

# Sends a random blog post from Planet Python to the user
@log_command
async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    latest_blogs = parse_planetpy_rss(10) # list of 10 dictionaries
    if not latest_blogs:
        await update.message.reply_text("Unable to reach latest Planet Python blog posts. Please try again later.")
        return
    random_blog = random.choice(latest_blogs) # selects a random blog post from the list
    message = f"{random_blog['title']}\n{random_blog['link']}"
    await update.message.reply_text(message) # sends the random blog post back to the user

# searches for blog posts with the provided keywords in the title and sends them back to the user
@log_command
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide the keywords to be searched for in the blog post title")
        return
    keywords = " ".join(context.args)
    posts = parse_planetpy_rss(50)
    matched_posts = []
    for p in posts:
        if keywords.lower() in p['title'].lower():
            matched_posts.append(p)
    if not matched_posts:
        await update.message.reply_text("Couldn't find any blog post with these keywords")
        return
    message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in matched_posts])
    await update.message.reply_text(message)

# counts the number of available blog posts and sends it back to the user
@log_command
async def count_command(update:Update, context: ContextTypes.DEFAULT_TYPE):
    posts = parse_planetpy_rss(50)
    count = len(posts)
    await update.message.reply_text(f"Number of available posts is {count}")

# searches for blog posts by the provided author name and sends them back to the user
@log_command
async def author_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide an author name")
        return
    author = " ".join(context.args)
    if not author.replace(" ","").isalpha():
        await update.message.reply_text("Please provide a valid author name")
        return
    posts = parse_planetpy_rss(50)
    matched_posts = []
    for p in posts:
        if p['title'].lower().startswith(author.lower()):
            matched_posts.append(p)
    if not matched_posts:
        await update.message.reply_text("Couldn't find any blog post by this author")
        return
    message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in matched_posts])
    await update.message.reply_text(message)

# subscribes the user to the bot and saves their chat ID and the number of blog posts they
#  want to receive per digest
@log_command
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        number = 10
    else:
        if context.args[0].isdigit():
            if int(context.args[0]) <= 10 and int(context.args[0]) >=0:
                number = int(context.args[0])
            else:
                await update.message.reply_text("Please provide a number 0-10")
                return
        else:
            await update.message.reply_text("Please provide a number 0-10")
            return
    chat_id = str(update.effective_chat.id)
    add_subscriber(chat_id, number)
    await update.message.reply_text(f"You're subscribed! You'll get {number} posts per digest at 16:00 UTC by default. Use /settime to change it.")


# Changes the time set for the daily posts sent by bot to subscribed users
@log_command
async def settime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide the hour and the minute you want the blog posts to be send at.")
        return
    if not (context.args[0].isdigit() and context.args[1].isdigit()):
        await update.message.reply_text("Please provide a valid hour 0-23 and a valid minute 0-59\n"
        "Example: /settime 14 24")
        return
    if not (int(context.args[0]) >= 0 and int(context.args[0]) <= 23 and int(context.args[1]) >=0 and int(context.args[1]) <= 59):
        await update.message.reply_text("Please provide a valid hour 0-23 and a valid minute 0-59")
        return
    hour = int(context.args[0])
    minute = int(context.args[1])
    chat_id = str(update.effective_chat.id)
    if not update_time(chat_id, hour, minute):
        await update.message.reply_text("You are not subscribed thus you can't set a time.\n"
        "You can subscribe using the /subscribe command. To see how to use it use /help command.")
        return
    await update.message.reply_text(f"Time succesfully changed to {hour}:{minute:02d}")


# unsubscribes the user from the bot and removes their chat ID from the list of subscribed users
@log_command
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    remove_subscriber(chat_id)
    await update.message.reply_text("Unsubscribed succesfully")

# sends the daily digest of blog posts to all subscribed users at 16:00 UTC
async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE):
    now = dt.datetime.now(dt.timezone.utc)
    chat_ids = get_due_subscribers(now.hour, now.minute)
    for row in chat_ids: 
        count = row["count"]
        posts = parse_planetpy_rss(count)
        if not posts:
            await context.bot.send_message(chat_id=row["chat_id"], text="Couldn't reach latest Planet Python blog posts. Please try again later.")
        else:
            message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in posts])
            await context.bot.send_message(chat_id=row["chat_id"], text=message)

# shows the current subscription status and count of blog posts per digest for the user
@log_command
async def mysettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    row = get_subscriber(chat_id)
    if row is None:
        await update.message.reply_text("Current Status: unsubscribed")
        return
    await update.message.reply_text(f"Current Status: subscribed, Count: {row['count']}, Time: {row['hour']}:{row['minute']:02d}")
    return



   