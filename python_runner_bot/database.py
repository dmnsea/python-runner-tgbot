import sqlite3

from .const import PYTHON_VERSIONS

db = sqlite3.connect("bot.db")

def prepare_db():
  cursor = db.cursor()
  cursor.execute(
    f'CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, lang TEXT, python TEXT DEFAULT "{PYTHON_VERSIONS[-1]}")'
  )
  db.commit()


def add_user(tgid, lang):
  cursor = db.cursor()
  cursor.execute("INSERT INTO users (telegram_id, lang) VALUES (?, ?)", [tgid, lang])
  db.commit()


def find_user(tgid):
  cursor = db.cursor()
  result = cursor.execute('SELECT * FROM users WHERE telegram_id = ?', [tgid])
  row = result.fetchone()
  if row:
    user = dict(telegram_id=row[0], lang=row[1], python=row[2])
    return user
  return None


def update_lang(tgid, lang):
  cursor = db.cursor()
  cursor.execute("UPDATE users SET lang = ? WHERE telegram_id = ?", [lang, tgid])
  db.commit()


def update_python(tgid, version):
  cursor = db.cursor()
  cursor.execute("UPDATE users SET python = ? WHERE telegram_id = ?", [version, tgid])
  db.commit()


def all_users():
  print("All users in db are:")
  cursor = db.cursor()
  rows = cursor.execute("SELECT * FROM users").fetchall()
  users = list(map(lambda r: dict(id=r[0], lang=r[1], python=r[2]), rows))
  for user in users:
    print(user)


def get_user_lang(tgid):
  user = find_user(tgid)
  if user:
    return user["lang"]
  return "en"


def get_user_python(tgid):
  user = find_user(tgid)
  if user:
    return user["python"]
  return PYTHON_VERSIONS[-1]
  

def close():
  db.close()

if __name__ == "__main__":
  all_users()
