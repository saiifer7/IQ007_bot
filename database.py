
import json
import os

DB_FILE = "users.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    db = load_db()
    return db.get(str(user_id))

def set_user(user_id, data):
    db = load_db()
    db[str(user_id)] = data
    save_db(db)

def find_user_by_username(username):
    db = load_db()
    for uid, user in db.items():
        if user.get("username") == username:
            return int(uid), user
    return None, None
