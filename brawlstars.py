import requests
import os 
from telegram import Update
from telegram.ext import ContextTypes

# Where the Brawl Stars API lives. Inside a container, 'localhost' means the
# container itself, so the host is reached via Docker's bridge gateway.
API_BASE = os.environ.get("BRAWL_API_BASE", "http://172.17.0.1:8000") # see why https -> http
# also see why change -p 127.0.0.1:8000:8000 -> 8000:8000

def _get(path, params=None):
    response = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def _post(path, body):
    response = requests.post(f"{API_BASE}{path}", json=body, timeout=10)
    response.raise_for_status()
    return response.json()

def _delete(path):
    response = requests.delete(f"{API_BASE}{path}", timeout=10)
    response.raise_for_status()

def _normalise(tag):
    new_tag = ""
    if tag.startswith("#"):
        for i in range(1, len(tag)):
            new_tag += tag[i]
    else:
        new_tag = tag
    return new_tag

# Finds which player(s) this chat is tracking. Returns None if none.
async def _tracked_player(update: Update):
    chat_id = str(update.effective_chat.id)
    try:
        players = _get("/players", {"chat_id": chat_id})
    except requests.RequestException:
        await update.message.reply_text("The stats service is unavailable.")
        return None

    if not players:
        await update.message.reply_text("You're not tracking anyone yet. Use /bs_track <tag> first.")
        return None

    return players[0]["tag"]  # first tracked player, if there are several

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("You need to provide your Brawl Stars tag.")
        return
    chat_id = str(update.effective_chat.id)
    tag = _normalise(context.args[0])
    body = {"tag" : tag, "chat_id" : chat_id}
    try:
        result = _post("/players", body)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            await update.message.reply_text("No player found with that tag.")
        elif e.response is not None and e.response.status_code == 502:
            await update.message.reply_text("Couldn't reach Brawl Stars API right now.")
        return
    except requests.RequestException:
        await update.message.reply_text("The stats service is unavailable.")
        return
    await update.message.reply_text(f"Now tracking {result['name']}. Stats will build up as you play.")

# /bs_untrack — stops tracking whichever player this chat registered
async def untrack_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = await _tracked_player(update)
    if tag is None:
        return
    
    try:
        _delete(f"/players/{tag.lstrip('#')}")
    except requests.RequestException:
        await update.message.reply_text("The stats service is unavailable.")
        return

    await update.message.reply_text("Stopped tracking. Your stored battles are kept.")


# /bs_stats [mode] — win/draw/loss record, optionally filtered by mode
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = await _tracked_player(update)
    if tag is None:
        return

    filters = {}
    if context.args:
        if _parse_filters(context.args, filters) == -1:
            await update.message.reply_text("Invalid user input: You forgot an '=' somewhere")
            return
    
    tag = tag.lstrip("#")
    try:
        record = _get(f"/players/{tag}/record", filters)
    except requests.RequestException:
        await update.message.reply_text("The stats service is unavailable.")
        return
    if record["total"] == 0:
        rate = 0
    else:
        rate = (record["wins"]/record["total"]) * 100
    await update.message.reply_text(
        f"Wins: {record['wins']}  Draws: {record['draws']}  Losses: {record['losses']}  "
        f"(Total of {record['total']} battles)\n"
        f"Win rate: {rate:.2f}%"
    )

# Parse filters from user input, returns -1 for invlaid user input
def _parse_filters(args, filters):
    for arg in args:
        if "=" not in arg:
            return -1
        key, value = arg.split("=", 1) # splits the two peices of info
        filters[key] = value.lower()
    return 1

        
# /bs_brawlers [map] — top brawlers by win rate, optionally filtered by map
async def brawlers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = await _tracked_player(update)
    if tag is None:
        return 

    filters = {}
    if context.args:
        if _parse_filters(context.args, filters) == -1:
            await update.message.reply_text("Invalid user input: You forgot an '=' somewhere")
            return
    
    tag = tag.lstrip("#")
    filters["min_matches"] = 1
    try:
        results = _get(f"/players/{tag}/brawlers", filters)
    except requests.RequestException:
        await update.message.reply_text("The stats service is unavailable.")
        return
    if not results:
        await update.message.reply_text("Not enough battles yet to rank your brawlers.")
        return

    lines = [
        f"{r['brawler']}: {r['wins']} Wins, {r['losses']} Losses, Win rate: {(r['wins']/r['total']) * 100:.2f} ({r['total']} matches)"
        for r in results
    ]
    await update.message.reply_text("\n".join(lines))