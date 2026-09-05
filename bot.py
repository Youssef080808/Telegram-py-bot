from telegram.ext import ApplicationBuilder, CommandHandler
import planetpy as p
import os
import brawlstars as b


BOT_TOKEN = os.environ.get("BOT_TOKEN") # replace with your bot token from BotFather

# if this script is being run directly, then execute the code not when being imported by something else
if __name__ == "__main__": 
    p.init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build() #creates a bot application
    app.add_handler(CommandHandler("start", p.start_command)) # calls start_command() when user sends /start command
    app.add_handler(CommandHandler("feed", p.feed_command)) # calls feed_command() when user sends /feed command
    app.add_handler(CommandHandler("help", p.help_command)) # calls help_command() when user sends /help command
    app.add_handler(CommandHandler("random", p.random_command)) # calls random_command() when user sends /random command
    app.add_handler(CommandHandler("search", p.search_command)) # calls search_command when user sends /search command
    app.add_handler(CommandHandler("count", p.count_command)) # calls count_command when user sends /count command 
    app.add_handler(CommandHandler("author", p.author_command)) # calls author_command when user sends /author command
    app.add_handler(CommandHandler("subscribe", p.subscribe_command)) # calls subscribe_command when user sends /subscribe command
    app.add_handler(CommandHandler("unsubscribe", p.unsubscribe_command)) # calls unsubscribe_command when user sends
    app.job_queue.run_repeating(p.send_daily_digest, interval=60, first=0) # schedules the send_daily_digest function to run every 60 seconds
    app.add_handler(CommandHandler("mysettings", p.mysettings_command)) # calls mysettings_command when user sends /mysettings command
    app.add_handler(CommandHandler("settime", p.settime_command)) # calls settime when user sends /settime command
    app.add_handler(CommandHandler("bs_track", b.track_command))
    app.add_handler(CommandHandler("bs_untrack", b.untrack_command))
    app.add_handler(CommandHandler("bs_stats", b.stats_command))
    app.add_handler(CommandHandler("bs_brawlers", b.brawlers_command))
    print("Bot is running...")
    app.run_polling() # starts the bot and keeps it running
