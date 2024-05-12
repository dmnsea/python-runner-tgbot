import json

strings = None

with open("strings.json", "r") as f:
  strings = json.loads(f.read())
  if not isinstance(strings, dict):
    raise SyntaxError("JSON object excpected to be in `strings.json`, but " +
                      type(strings) + " received")


def get(key, lang):
  if key in strings[lang]:
    return strings[lang][key]
  return f"{key} not found among [{list(strings[lang].keys())}]"


def get_languages(lang):
  keys = list(strings.keys())
  langs = []
  for key in keys:
    name = "- " + get(key+"_lang_name", lang) + f"  ('{key}')"
    langs.append(name)
  return langs

def get_lang_codes():
  return list(strings.keys())