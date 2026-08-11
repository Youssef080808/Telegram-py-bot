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

BOT_TOKEN = "PASTE_TOKEN_HERE" 

# Parses first 10 items from http://planetpython.org/rss20.xml and returns a list of 
# dictionaries with the title, link, and description of each item.
def parse_planetpy_rss():
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
    return items[:10]# return the first 10 items from the list of dictionaries

# runs when someone send /start command to the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send /feed to get the latest Python blog posts.")
    #update contains info about incoming message, and bot replies back

# runs when someone send /feed command to the bot
async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = parse_planetpy_rss() # list of 10 dictionaries
    message = "\n\n".join([f"{p['title']}\n{p['link']}" for p in posts]) # COMPACT LOOP to 
    #create a string with the titles and links of the latest blog posts
    await update.message.reply_text(message) # sends combined message back to the user 
    # with the titles and links of the latest blog posts

if __name__ == "__main__": # if this script is being run directly, then execute the code
    app = ApplicationBuilder().token(BOT_TOKEN).build() #creates a bot application
    app.add_handler(CommandHandler("start", start)) # calls start() when user sends /start command
    app.add_handler(CommandHandler("feed", feed)) # calls feed() when user sends /feed command
    print("Bot is running...")
    app.run_polling() # starts the bot and keeps it running
