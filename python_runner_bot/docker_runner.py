import asyncio
from json import dumps
from logging import getLogger
from time import time
import re

from aiogram.types import Message
# https://docker-py.readthedocs.io/en/stable/
import docker
from requests import post

from . import const
from . import database as db
from . import localization as lc

#: Объект для взаимодействия с Docker Engine
client = docker.from_env()
#: Объект для логгирования
log = getLogger("docker_runner")

#############################################
#############################################
#############################################

def prepare_image(target: str = const.DEFAULT_IMAGE) -> None:
  """
    Подготовка указанного образа Docker - поиск среди уже загруженных и загрузка при отсутствии такового.

    :param target: Наименование требуемого образа
    :type target: str
  """
  global client
  found = False
  log.info(f"Checking for '{target}' image availability")
  for image in client.images.list():
    for tag in image.tags:
      if tag == target:
        found = True
        break
  if not found:
    log.info(f"Image '{target}' not found, pulling")
    client.images.pull(target)
    log.info(f"Image '{target}' pulled")
  else:
    log.info(f"Image '{target}' found")

#############################################
#############################################
#############################################

async def run_container(cmd: str, lang: str, user_id: int, target: str = const.DEFAULT_IMAGE) -> str:
  global client
  """
    Функция для запуска Docker контейнера с указанной командой на базе указанного образа, а также получения результатов выполнения.

    :param cmd: Строкое представление списка элементов команды
    :type cmd: str

    :param lang: Код предпочитаемой пользователем локализации
    :type lang: str

    :param user_id: Идентификатор пользователя, используемый в логах и названии контейннера
    :type user_id: int

    :param target: Требуемый Docker-образ, по умолчанию - значение из модуля констант
    :type target: str

    :return: Результат работы контейнера (логи потоков вывода и ошибок)
    :rtype: str

    Неизменяемые параметры запускаемых контейнеров:
    - detach=True - запуск контейнера в фоновом режиме. Предотвращает исключение типа ContainerError в случае если запусщенный в контейнере процесс завершился с ненулевым кодом.
    - mem_limit=CONTAINER_MEMORY_LIMIT_MB - ограничение по памяти, используется соответствующее значение из модуля констант
    - network_disabled=True - отключение сетевого доступа во избежание потенциальных нарушений условий сервиса, где запущен бот (исключение загрузки или отправки каких-то потенциально вредоносных данных, исключение сканирования сетей и т.д.)
    - read_only=True - минимизация влияния пользовательского кода на среду в контейнере (редактирование файлов системы базового образа, "снос" системы и т.д.)
  """
  container_name = f"code_{user_id}_{time()}"
  log.info(f"Running code for {user_id} with {target} image: {container_name}")

  container = client.containers.run(
      image=target,
      command=cmd,
      name=container_name,
      detach=True,
      mem_limit=f"{const.CONTAINER_MEMORY_LIMIT_MB}m",
      network_disabled=True,
      read_only=True
  )
  counter = 0
  step = 0.1
  execution_timeout = False
  while(container.status != "exited"):
    if(counter > const.CONTAINER_EXECUTION_TIMEOUT):
      container.reload()
      if container.status == "running":
        execution_timeout = True
      container.stop(timeout=const.CONTAINER_STOP_TIMEOUT)
      log.info(f"Stopping {container_name} due to timeout")
      break
    await asyncio.sleep(step)
    counter += step
    container.reload()
  container.reload()
  log.info(f"Container {container_name} stopped")
  stdout = container.logs(stdout=True,stderr=False).decode("utf-8")
  stderr = container.logs(stdout=False,stderr=True).decode("utf-8")
  container.remove(force=True)
  log.info(f"Container {container_name} removed")

  output=""
  if stdout:
    output += f"STDOUT:\n{stdout}"
  if stderr:
    output += "\n\n\nSTDERR:\n" + stderr.replace('File "<string>"', f'File "code_{user_id}.py"')
  if execution_timeout:
    output += f"\n\n\nEXECUTION TIMEOUT ({const.CONTAINER_EXECUTION_TIMEOUT} SEC)"
  output = output.strip()
  if not output:
    output = lc.get("empty_output", lang)
  return output

#############################################
#############################################
#############################################

# code: str, edit_func: Callable, inline: int = None
async def run_python_code(code: str, msg: Message, user_id: int):
  """
    Формирование команды на запуск Python кода в контейнере с использованием предпочитаемой пользователем версии Python (образа). Запуск и ожидание результатов работы контейнера. В процессе работы запрашивает комментарий от ИИ при наличии чего-либо в потоке ошибок (STDERR) и редактирует сообщение, указывая этап выполнения (начато выполнение, получен результат, запрос комментария ИИ при ошибке, отправка итогового результата пользователю)

    :param code: Текст, трактуемый как код на языке Python
    :type code: str

    :param msg: Объект сообщения с необходимой для редактирования текста сообщения информацией и методом
    :type msg: aiogram.types.Message

    :param user_id: Идентификатор пользователя, используемый для получения настроек пользователя и использования в функции запуска контейнера
    :type user_id: int
  """
  try:
    lang = db.get_user_lang(user_id)
    python_version = db.get_user_python(user_id)
    image = f"python:{python_version}"
    command = ["python3", "-c", code]
    await msg.edit_text(lc.get("started_exec", lang))
    log.info(f"Informed user:{user_id} about code execution start")
    output = await run_container(
      cmd = command,
      user_id = user_id,
      target=image,
      lang=lang
    )
    log.info(f"Got result for user:{user_id}")
    if "STDERR" in output:
      log.info(f"Asking AI about STDERR for user:{user_id}")
      await msg.edit_text(lc.get("waiting_ai", lang))
      explanation = ai_explain(output, lang, python_version)
      output += "\n\n\n" + lc.get("ai_comment", lang) + explanation
    await msg.edit_text(output)
    db.close()
    log.info(f"Finished processing code for user:{user_id}")
  except Exception as e:
    print("Exception:", e)

#############################################
#############################################
#############################################

async def test_run():
  """
    Функция для проведения тестового прогона с замерами времени между запуском контейнера и запуском кода, а также между завершением работы кода и удалением контейнера.

    :return: Сообщение с временными метками и расчитанным временем оверхеда
    :rtype: str
  """
  starting_time = time()
  sleep_time=3
  python_code = \
f"""
from time import time, sleep
starting_time = {starting_time}
now = time()
print("User script execution started: ", now)
print("Code launch overhead: ", round(now - starting_time, 3), "seconds")
print("Sleep for {sleep_time} second(s)")
sleep({sleep_time})
print("User script finished: ",time())
"""
  cmd = ["python3", "-c", python_code]
  report = f"Time before starting container: {starting_time}"
  container = client.containers.run(
      image=const.DEFAULT_IMAGE,
      command=cmd,
      name=f"py-runner-time-test",
      detach=True,
      mem_limit=f"{const.CONTAINER_MEMORY_LIMIT_MB}m",
      network_disabled=True,
      read_only=True
  )
  counter = 0
  step = 0.1
  while(container.status != "exited"):
    if(counter > const.CONTAINER_EXECUTION_TIMEOUT):
      break
    await asyncio.sleep(step)
    counter += step
    container.reload()
  report += '\n' + container.logs().decode("utf-8") + f'Container stoped at {time()}'
  container.remove(force=True)
  ending_time = time()
  report += f'\nContainer removed at {ending_time}'

  regex = re.compile(r"User script finished:  (?P<timing>[0-9.]+)")
  match = regex.search(report)
  if match:
    user_script_finished = float(match.group("timing"))
    report += f"\nFinish(stop and remove container) overhead: {round(ending_time - user_script_finished,3)} seconds"
  else:
    report += "\nIf you changed output template for this test run, then it seems that you have not edited your regular expression properly to detect finish time of user's script"
  return report


def init():
  """
    Подготовка всех образов с версиями Python, перечисленными в модуле констант
  """
  log.info("Preparing images")
  for version in const.PYTHON_VERSIONS:
    prepare_image(f"python:{version}")


def ai_explain(execution_result, lang, python_version) -> str:
  """
    Запрос комментария от ИИ. Работает на основе публичного API из открытых источников.

    :param execution_result: Результат выполнения
    :type execution_result: str

    :param lang: Код используемой локализации
    :type lang: str

    :param python_version: Используемая версия Python
    :type python_version: str

    :return: Ответ от ИИ
    :rtype: str
  """
  url = "https://nexra.aryahcr.cc/api/chat/gpt"
  headers = {"Content-Type": "application/json"}
  data = {
      "messages": [{
          "role": "user",
          "content": lc.get("code_exec_result", lang).format(version=python_version) + "\n\n" + execution_result
      }],
      "prompt": lc.get("explain_prompt", lang),
      "model": "GPT-4",
      "markdown": False
  }

  try:
    response = post(url, headers=headers, data=dumps(data))
    if response.status_code == 200:
      return response.json()["gpt"]
    else:
      return f"Error: {response.status_code}"
  except Exception as e:
    return str(e)