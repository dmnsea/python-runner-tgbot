import asyncio
from json import dumps
from logging import getLogger
from time import time
from typing import Callable, Coroutine
import re

from aiogram.types import Message
# https://docker-py.readthedocs.io/en/stable/
import docker
from requests import post

from . import const
from . import database as db
from . import localization as lc

client = docker.from_env()
log = getLogger("docker_runner")

#############################################
#############################################
#############################################

def prepare_image(target: str = const.DEFAULT_IMAGE) -> None:
  global client
  f"""Function to prepare necessary docker image for futher work of bot.

  1. target (str, optional): Target image in next format: "image_tag:version_tag". Defaults to DEFAULT_IMAGE.
  """
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
  """Function to run specified offline container with specified command.

  1. cmd (str): Command for the container. For running python code it's f'python -c "{code_to_run}"'.
  2. id (int): supposed to be telegram id or chat id, used to make unique container name (which will also include timestamp in name)
  2. target (str, optional): Target image in next format: "image_tag:version_tag". Defaults to DEFAULT_IMAGE.

  Hardcoded container parameters:
  - name=py-runner-id-timestamp
  - detach=True - container starts detached, this way exclude ContainerError exception, when some exception raised inside container and it's finishing with non-zero code
  - mem_limit=CONTAINER_MEMORY_LIMIT_MB - value from constants file. Limits the 
  - network_disabled=True - preventing network abuse
  - read_only=True - preventing "rm -rf /" and others
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
  Some kind of benchmarking function. Made to measure overheads of running, stopping and removing container
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
  log.info("Preparing images")
  for version in const.PYTHON_VERSIONS:
    prepare_image(f"python:{version}")


def ai_explain(execution_result, lang, python_version) -> str:
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