import json
from pathlib import Path

from . import const

#: Словарь для считанных из файла строк локализаций
strings = None

def init():
  """
    Чтение файла локализации в словарь `strings`
  """
  global strings
  lc_file = Path(const.BASE_DIR).joinpath("strings.json")
  with open(lc_file, "r") as f:
    strings = json.loads(f.read())
    if not isinstance(strings, dict):
      raise SyntaxError(f"JSON object excpected to be in `{lc_file.absolute()}`, but {type(strings)} received")

def get(key, lang):
  """
    Получение строки из заданной локализации

    :param key: Ключ (идентификатор) требуемой строки
    :type key: int

    :param lang: Код локализации
    :type lang: str

    :return: Строка на требуемом языке либо сообщение о том, что не найдена требуемая строка
    :rtype: str
  """
  global strings
  if key in strings[lang]:
    return strings[lang][key]
  return f"{key} not found among [{list(strings[lang].keys())}]"


def get_languages(lang):
  """
    Получение списка локализаций с обозначением на заданном языке

    :param lang: Код локализации для результата
    :type lang: str

    :return: Список локализаций
    :rtype: list[str]
  """
  global strings
  keys = list(strings.keys())
  langs = []
  for key in keys:
    name = "- " + get(key+"_lang_name", lang) + f"  ('{key}')"
    langs.append(name)
  return langs

def get_lang_codes():
  """
    Получение списка кодов локализаций

    :return: Список локализаций
    :rtype: list[str]
  """
  global strings
  return list(strings.keys())