import asyncio
from time import time
from typing import Callable
import re

# https://docker-py.readthedocs.io/en/stable/
import docker

import const

client = docker.from_env()

#############################################
#############################################
#############################################

def prepare_image(target: str = const.DOCKER_DEFAULT_IMAGE) -> None:
  global client
  f"""Function to prepare necessary docker image for futher work of bot.

  1. target (str, optional): Target image in next format: "image_tag:version_tag". Defaults to DEFAULT_DOCKER_IMAGE.
  """
  found = False
  for image in client.images.list():
    for tag in image.tags:
      if tag == target:
        found = True
        break
  if not found:
    client.images.pull(target)

#############################################
#############################################
#############################################

async def run_container(cmd: str, msg_id:str, filename: str, target: str = const.DOCKER_DEFAULT_IMAGE) -> str:
  global client
  """Function to run specified offline container with specified command.

  1. cmd (str): Command for the container. For running python code it's f'python -c "{code_to_run}"'.
  2. id (int): supposed to be telegram id or chat id, used to make unique container name (which will also include timestamp in name)
  2. target (str, optional): Target image in next format: "image_tag:version_tag". Defaults to DEFAULT_DOCKER_IMAGE.

  Hardcoded container parameters:
  - name=py-runner-id-timestamp
  - detach=True - container starts detached, this way exclude ContainerError exception, when some exception raised inside container and it's finishing with non-zero code
  - mem_limit=DOCKER_CONTAINER_MEMORY_LIMIT - value from constants file. Limits the 
  - network_disabled=True - preventing network abuse
  - read_only=True - preventing "rm -rf /" and others
  """
  container = client.containers.run(
      image=const.DOCKER_DEFAULT_IMAGE,
      command=cmd,
      name=f"py-runner-{msg_id}-{time()}",
      detach=True,
      mem_limit=f"{const.DOCKER_CONTAINER_MEMORY_LIMIT_MB}m",
      network_disabled=True,
      read_only=True
  )
  counter = 0
  step = 0.1
  execution_timeout = False
  while(container.status != "exited"):
    if(counter > const.DOCKER_CONTAINER_EXECUTION_TIMEOUT):
      container.reload()
      if container.status == "running":
        execution_timeout = True
      container.stop(timeout=const.DOCKER_CONTAINER_STOP_TIMEOUT)
      break
    await asyncio.sleep(step)
    counter += step
    container.reload()
  container.reload()
  stdout = container.logs(stdout=True,stderr=False).decode("utf-8")
  stderr = container.logs(stdout=False,stderr=True).decode("utf-8")
  container.remove(force=True)

  output=""
  if stdout:
    output += f"STDOUT:\n{stdout}"
  if stderr:
    output += "\n\n\nSTDERR:\n" + stderr.replace('File "<string>"', f'File "{filename}"')
  if execution_timeout:
    output += f"\n\n\nExecution timeout ({const.DOCKER_CONTAINER_EXECUTION_TIMEOUT} seconds)"
  output = output.strip()
  if not output:
    output = "strings.empty_output()"
  return output

#############################################
#############################################
#############################################

# code: str, edit_func: Callable, inline: int = None
def run_python_code(code: str, edit_func: Callable, msg_id: str, filename: str):
  command = ["python3", "-c", code]
  print("run_python_code started")
  edit_func("strings.running()")

  print("Sent RUNNING status")
  output = asyncio.run(
    run_container(
      cmd = command,
      msg_id = msg_id,
      filename = filename
    )
  )
  print("Execution finished, sending output")

  edit_func(output)
  
  print("Execution output sent")

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
      image=const.DOCKER_DEFAULT_IMAGE,
      command=cmd,
      name=f"py-runner-time-test",
      detach=True,
      mem_limit=f"{const.DOCKER_CONTAINER_MEMORY_LIMIT_MB}m",
      network_disabled=True,
      read_only=True
  )
  counter = 0
  step = 0.1
  while(container.status != "exited"):
    if(counter > const.DOCKER_CONTAINER_EXECUTION_TIMEOUT):
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
    report += f"\nFinish(stop and remove container) overhead: {round(ending_time - user_script_finished,3)}±{step} seconds"
  else:
    report += "\nIf you changed output template for this test run, then it seems that you have not edited your regular expression properly to detect finish time of user's script"
  return report

def init():
  for version in const.PYTHON_VERSIONS:
    prepare_image(f"python:{version}")