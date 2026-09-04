import re
import time
from collections import defaultdict, deque

ABUSE_WORDS = {
    "bc", "mc", "madarchod", "bhosdike", "chutiya", "gandu",
    "harami", "fuck", "fucker", "motherfucker"
}
FOOD_WORDS = {
    "pizza", "burger", "food", "biryani", "chicken", "momos",
    "fries", "noodles"
}

class Moderation:
    def __init__(self, db):
        self.db = db
        self.recent = defaultdict(lambda: deque(maxlen=6))

    def check(self, message):
        text = (message.text or message.caption or "").lower()
        if not text:
            return None
        settings = self.db.get_settings(message.chat.id)

        words = set(re.findall(r"[a-z0-9']+", text))
        if settings["abuse_filter"] and words & ABUSE_WORDS:
            return "Abusive language"

        if settings["anti_food"] and words & FOOD_WORDS:
            return "Food filter"

        if settings["anti_spam"]:
            key = (message.chat.id, message.from_user.id)
            now = time.time()
            q = self.recent[key]
            q.append((now, text))
            if len(q) >= 5 and now - q[0][0] <= 12:
                return "Spam/flood detected"
        return None
