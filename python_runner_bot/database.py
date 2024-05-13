import sqlite3

from .const import PYTHON_VERSIONS

#: Открытие БД для дальнейшей работы с ней
db = sqlite3.connect("bot.db")

def prepare_db():
  """
  Инициализация базы данных - создание таблицы `users` с полями: 

  - `telegram_id`

  - `lang` (код локализации)

  - `python` (используемая версия, по умолчанию - берется значение из модуля с константами)
  """
  cursor = db.cursor()
  cursor.execute(
    f'CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, lang TEXT, python TEXT DEFAULT "{PYTHON_VERSIONS[-1]}")'
  )
  db.commit()


def add_user(tgid, lang):
  """
    Добавление пользователя в базу данных

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :param lang: Код используемой локализации
    :type lang: str

  """
  cursor = db.cursor()
  cursor.execute("INSERT INTO users (telegram_id, lang) VALUES (?, ?)", [tgid, lang])
  db.commit()


def find_user(tgid):
  """
    Поиск пользователя в базе данных

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :return: Словарь со всеми столбцами записи из БД
    :rtype: dict[telegram_id, lang, python] или None
  """
  cursor = db.cursor()
  result = cursor.execute('SELECT * FROM users WHERE telegram_id = ?', [tgid])
  row = result.fetchone()
  if row:
    user = dict(telegram_id=row[0], lang=row[1], python=row[2])
    return user
  return None


def update_lang(tgid, lang):
  """
    Смена кода локализации в базе данных

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :param lang: Задаваемый код локализации
    :type lang: str

  """
  cursor = db.cursor()
  cursor.execute("UPDATE users SET lang = ? WHERE telegram_id = ?", [lang, tgid])
  db.commit()


def update_python(tgid, version):
  """
    Смена версии python в базе данных

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :param lang: Задаваемая версия Python
    :type lang: str

  """
  cursor = db.cursor()
  cursor.execute("UPDATE users SET python = ? WHERE telegram_id = ?", [version, tgid])
  db.commit()


def all_users():
  """
    Отображение списка пользователей при выполнении модуля напрямую
  """
  print("All users in db are:")
  cursor = db.cursor()
  rows = cursor.execute("SELECT * FROM users").fetchall()
  users = list(map(lambda r: dict(id=r[0], lang=r[1], python=r[2]), rows))
  for user in users:
    print(user)


def get_user_lang(tgid):
  """
    Получение кода заданной для пользователя локализации

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :return: Код локализации, по умолчанию - "en"
    :rtype: str
  """
  user = find_user(tgid)
  if user:
    return user["lang"]
  return "en"


def get_user_python(tgid):
  """
    Получение заданной для пользователя версии Python

    :param tgid: Идентификатор пользователя
    :type tgid: int

    :return: Код локализации, по умолчанию - соответствующее значение из модуля констант
    :rtype: str
  """
  user = find_user(tgid)
  if user:
    return user["python"]
  return PYTHON_VERSIONS[-1]
  

def close():
  """
    Закрытие соединения с базой данных
  """
  db.close()

if __name__ == "__main__":
  all_users()
