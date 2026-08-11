"""from telegram import Bot, Update # to use Bot tool from telegram librar(to interact with 
#Telegram API)
import asyncio # tasks involving waiting for events to happen, such as waiting for a response from a server or waiting for a user to input data.
BOT_TOKEN = 'TOKEN'
async def main():# function that waits on something
    bot = Bot(token=BOT_TOKEN)# connects to the Telegram API using the provided bot token
    #me = await bot.get_me()# asks telegram API for information about the bot itself
    #print(me)
    updates = await bot.get_updates(858465595+1)# asks telegram API for any new messages or 
    # updates that have been sent to the bot
    print(updates)
asyncio.run(main())"""

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import xml.etree.ElementTree as cElementTree
import random

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE" 

# Parses first 10 items from http://planetpython.org/rss20.xml and returns a list of 
# dictionaries with the title, link, and description of each item.
def parse_planetpy_rss(number : int):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get("https://planetpython.org/rss20.xml", headers=headers) # GET request to download the 
    # RSS feed from the specified URL
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
    return items[:number]# return the first 10 items from the list of dictionaries

# runs when someone send /start command to the bot, update is info about incoming message and
# context is extra tools and info, "starts the bot and sends a welcome message to the user"
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send /help to see all available commands.")
    # update contains info about incoming message, and bot replies back

# runs when someone send /feed command to the bot, "gets 10 latest blog posts from planetpython.org"
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
    message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in posts]) # COMPACT LOOP to 
    # create a string with the titles and links of the latest blog posts
    await update.message.reply_text(message) # sends combined message back to the user 
    # with the titles and links of the latest blog posts
# runs when someone send /help command to the bot, "shows current available commands"
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("These are the commands you can use:\n"
    "/start: starts the bot\n"
    "/feed x: gets the x latest blog posts from Planet Python or 10 if no number provided\n"
    "/help: shows available commands\n"
    "/random: gets a random blog post from Planet Python"
    )
async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    latest_blogs = parse_planetpy_rss(10) # list of 10 dictionaries
    random_blog = random.choice(latest_blogs) # selects a random blog post from the list
    message = f"{random_blog['title']}\n{random_blog['link']}"
    await update.message.reply_text(message) # sends the random blog post back to the user



if __name__ == "__main__": # if this script is being run directly, then execute the code
    app = ApplicationBuilder().token(BOT_TOKEN).build() #creates a bot application
    app.add_handler(CommandHandler("start", start_command)) # calls start_command() when user sends /start command
    app.add_handler(CommandHandler("feed", feed_command)) # calls feed_command() when user sends /feed command
    app.add_handler(CommandHandler("help", help_command)) # calls help_command() when user sends /help command
    app.add_handler(CommandHandler("random", random_command)) # calls random_command() when user sends /random command
    print("Bot is running...")
    app.run_polling() # starts the bot and keeps it running
