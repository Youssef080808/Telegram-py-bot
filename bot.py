from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import xml.etree.ElementTree as cElementTree
import random
import json
import datetime as dt
import time

BOT_TOKEN = "PASTE_TOKEN_HERE"

cache = {"data": None, "timestamp": 0}

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

def log_command(func):
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        with open("bot.log", "a") as f:
            f.write(f"{chat_id} - {func.__name__} - {dt.datetime.now()}\n")
        return await func(update, context)
    return wrapper   
    


# ANY FUNCTION THAT TALKS TO THE TELEGRAM SERVERS USES ASYNC AND AWAIT

# runs when someone send /start command to the bot, update is info about incoming message and
# context is extra tools and info, "starts the bot and sends a welcome message to the user"
@log_command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send /help to see all available commands.")
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
# runs when someone send /help command to the bot, "shows current available commands"
@log_command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("These are the commands you can use:\n"
    "/start: starts the bot\n"
    "/feed x: gets the x latest blog posts from Planet Python or 10 if no number provided\n"
    "/help: shows available commands\n"
    "/random: gets a random blog post from Planet Python\n"
    "/search keywords: searches for blog posts with the provided keywords in the title\n"
    "/count: counts the number of available blog posts\n"
    "/author name: searches for blog posts by the provided author name\n"
    "/subscribe x: subscribes to the bot and gets x latest blog posts per digest or 10 if no number provided\n"
    "/unsubscribe: unsubscribes from the bot\n"
    "/mysettings: shows your current subscription status and count of blog posts per digest\n"
    )
@log_command
async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    latest_blogs = parse_planetpy_rss(10) # list of 10 dictionaries
    if not latest_blogs:
        await update.message.reply_text("Couldn't reach latest Planet Python blog posts. Please try again later.")
        return
    random_blog = random.choice(latest_blogs) # selects a random blog post from the list
    message = f"{random_blog['title']}\n{random_blog['link']}"
    await update.message.reply_text(message) # sends the random blog post back to the user
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
@log_command
async def count_command(update:Update, context: ContextTypes.DEFAULT_TYPE):
    posts = parse_planetpy_rss(50)
    count = len(posts)
    await update.message.reply_text(f"Number of available posts is {count}")
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
def get_chat_ids():
    try:
        with open("subscribers.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}  
def save_subs(subs : dict):
    with open("subscribers.json", "w") as f:
        json.dump(subs,f)
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
    chat_ids = get_chat_ids()
    chat_ids[chat_id] = number
    save_subs(chat_ids)
    await update.message.reply_text(f"You're subscribed! You'll get {number} posts per digest.")
@log_command
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_ids = get_chat_ids()
    chat_id = str(update.effective_chat.id)
    chat_ids.pop(chat_id, None)
    save_subs(chat_ids)
    await update.message.reply_text("Unsubscribed succesfully")
async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE):
    chat_ids = get_chat_ids()
    for chat_id in chat_ids:
        number = chat_ids[chat_id]
        posts = parse_planetpy_rss(number)
        if not posts:
            await context.bot.send_message(chat_id=chat_id, text="Couldn't reach latest Planet Python blog posts. Please try again later.")
        else:
            message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in posts])
            await context.bot.send_message(chat_id=chat_id, text=message)
@log_command
async def mysettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_ids = get_chat_ids()
    chat_id = str(update.effective_chat.id)
    current = chat_ids.get(chat_id, None) # return value (count) associated with key (chat_id)
    if current is None:
        await update.message.reply_text("Current Status: unsubscribed")
        return
    await update.message.reply_text(f"Current Status: subscribed, Count: {current}")
    return


if __name__ == "__main__": # if this script is being run directly, then execute the code
    app = ApplicationBuilder().token(BOT_TOKEN).build() #creates a bot application
    app.add_handler(CommandHandler("start", start_command)) # calls start_command() when user sends /start command
    app.add_handler(CommandHandler("feed", feed_command)) # calls feed_command() when user sends /feed command
    app.add_handler(CommandHandler("help", help_command)) # calls help_command() when user sends /help command
    app.add_handler(CommandHandler("random", random_command)) # calls random_command() when user sends /random command
    app.add_handler(CommandHandler("search", search_command)) # calls search_command when user sends /search command
    app.add_handler(CommandHandler("count", count_command)) # calls count_command when user sends /count command 
    app.add_handler(CommandHandler("author", author_command)) # calls author_command when user sends /author command
    app.add_handler(CommandHandler("subscribe", subscribe_command)) # calls subscribe_command when user sends /subscribe command
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command)) # calls unsubscribe_command when user sends
    app.job_queue.run_daily(send_daily_digest, time=dt.time(hour=16,minute=00)) # schedules send_daily_digest() to run every day at 16:00 UTC
    app.add_handler(CommandHandler("mysettings", mysettings_command)) # calls mysettings_command when user sends /mysettings command
    print("Bot is running...")
    app.run_polling() # starts the bot and keeps it running
