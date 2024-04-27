import json
import random
import requests


def run(code, editor, msg_id, filename):
  result = random.choice([success, error, timeout])
  if result == error:
    result = result.format(filename)
  return result


timeout = """
from time import sleep
CODE:
print("Hello world")
sleep(15)
print("wake up")

STDOUT:
hello world



Execution timeout (10 seconds)
""".strip()

error = """
CODE:
print("Hello world)
print([1,2,3].findFirst(4))

STDOUT:
hello world



STDERR:
Traceback (most recent call last):
  File "{}", line 4, in <module>
AttributeError: 'list' object has no attribute 'findFirst'
""".strip()

success = """
CODE:
print("Hello world)

STDOUT:
hello world
""".strip()


def explain(execution_result, user_lang, python_version="3.11.4") -> str:
  url = "https://nexra.aryahcr.cc/api/chat/gpt"

  headers = {"Content-Type": "application/json"}

  data = {
      "messages": [{
          "role": "user",
          "content": f"Python v{python_version} code execution result\n\n" + execution_result
      }],
      "prompt": "Объясни в чем ошибка, которая описана в разделе STDERR", # заменить на локализованное сообщение
      "model": "GPT-4",
      "markdown": False
  }

  try:
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
      # Modify your code to remove the '_' at the end of the output
      return response.json()["gpt"]
    else:
      return f"Error: {response.status_code}"
  except Exception as e:
    return str(e)
