import json
import os
import planetpy as p

def migrate():
    json_path = os.path.join(p.DATA_DIR, "subscribers.json")
    if not os.path.exists(json_path):
        print("No subscribers.json found, nothing to migrate.")
        return

    with open(json_path, "r") as f:
        subs = json.load(f)

    p.init_db()
    for chat_id, settings in subs.items(): # items() give the key and value
        p.add_subscriber(chat_id, settings["count"], settings["hour"], settings["minute"])

    print(f"Migrated {len(subs)} subscriber(s) to {p.DB_PATH}")

if __name__ == "__main__":
    migrate()