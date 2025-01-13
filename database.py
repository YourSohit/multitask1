try:
    from pymongo import MongoClient
except ImportError:
    raise ImportError("The 'pymongo' library is not installed. Install it using 'pip install pymongo'.")

from config import DATABASE_URL
from datetime import datetime, timedelta

client = MongoClient(DATABASE_URL)
db = client.get_database("MultitaskingBot")
users_collection = db.get_collection("users")

# Add or update user
def add_user(user_id, username):
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({
            "user_id": user_id,
            "username": username,
            "is_premium": False,
            "task_count": 0,
            "premium_expiry": None
        })

def increment_task_count(user_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"task_count": 1}}
    )

def decrement_task_count(user_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"task_count": -1}}
    )

def get_task_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("task_count", 0) if user else 0

def is_premium(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user and user.get("premium_expiry"):
        return datetime.utcnow() < user["premium_expiry"]
    return False

def set_premium(user_id, days):
    expiry_date = datetime.utcnow() + timedelta(days=days)
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"is_premium": True, "premium_expiry": expiry_date}}
    )

def get_user_plan(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user:
        expiry = user.get("premium_expiry")
        if expiry:
            return {"is_premium": True, "expiry": expiry}
    return {"is_premium": False}
