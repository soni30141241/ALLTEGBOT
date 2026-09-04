import sqlite3
import threading

class Database:
    def __init__(self, path="bot.db"):
        self.path = path
        self.lock = threading.Lock()
        self._init()

    def conn(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self.conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS members(
                chat_id INTEGER, user_id INTEGER, name TEXT,
                PRIMARY KEY(chat_id,user_id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS warnings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER, user_id INTEGER, reason TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS settings(
                chat_id INTEGER PRIMARY KEY,
                anti_spam INTEGER DEFAULT 1,
                abuse_filter INTEGER DEFAULT 1,
                anti_food INTEGER DEFAULT 0,
                warn_limit INTEGER DEFAULT 3)""")

    def save_member(self, chat_id, user_id, name):
        with self.conn() as c:
            c.execute("INSERT OR REPLACE INTO members VALUES(?,?,?)", (chat_id,user_id,name))

    def get_members(self, chat_id):
        with self.conn() as c:
            return c.execute("SELECT user_id,name FROM members WHERE chat_id=?", (chat_id,)).fetchall()

    def add_warn(self, chat_id, user_id, reason):
        with self.conn() as c:
            c.execute("INSERT INTO warnings(chat_id,user_id,reason) VALUES(?,?,?)", (chat_id,user_id,reason))
            return c.execute("SELECT COUNT(*) FROM warnings WHERE chat_id=? AND user_id=?", (chat_id,user_id)).fetchone()[0]

    def warn_count(self, chat_id, user_id):
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM warnings WHERE chat_id=? AND user_id=?", (chat_id,user_id)).fetchone()[0]

    def reset_warns(self, chat_id, user_id):
        with self.conn() as c:
            c.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id,user_id))

    def get_settings(self, chat_id):
        with self.conn() as c:
            row = c.execute("SELECT anti_spam,abuse_filter,anti_food,warn_limit FROM settings WHERE chat_id=?", (chat_id,)).fetchone()
            if not row:
                c.execute("INSERT INTO settings(chat_id) VALUES(?)", (chat_id,))
                return {"anti_spam":1,"abuse_filter":1,"anti_food":0,"warn_limit":3}
            return dict(zip(["anti_spam","abuse_filter","anti_food","warn_limit"], row))

    def set_warn_limit(self, chat_id, limit):
        self.get_settings(chat_id)
        with self.conn() as c:
            c.execute("UPDATE settings SET warn_limit=? WHERE chat_id=?", (limit,chat_id))
