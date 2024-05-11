from concurrent.futures import ThreadPoolExecutor
import pickle
from queue import Queue
import time
from pathlib import Path

from typing import Callable

import const
from docker_runner import run_python_code

class ExecutorQueue:

  # queue task is dict[code:str, edit_function:typing.Callable]
  _code_queue: Queue = None
  _executorPool: ThreadPoolExecutor = None
  _actual_threads: int = 0
  _active: bool = True


  @staticmethod
  def add_task(code: str, edit_func: Callable, msg_id: str):
    print("Added new task to queue")
    ExecutorQueue._code_queue.put(dict(code=code, edit_func=edit_func, msg_id=msg_id))


  @staticmethod
  def process_task(tasks_queue, number):
    print(f"Executor #{number} ready to work")
    while ExecutorQueue._active:
      if tasks_queue.empty():
        time.sleep(0.5)
        continue
      task: dict[str, Message] = tasks_queue.get()
      print(f"Task handled by thread#{number}")
      try:
        run_python_code(code=task['code'], edit_func=task['edit_func'], msg_id=task['msg_id'], filename=f"code_executor_{number}.py")
        print(f"Queue size now ~{tasks_queue.qsize()} tasks")
      except Exception as e:
        print(e)
    print(f"Executor #{number} shuting down")


  @staticmethod
  def restore_queue():
    tasks = []
    bkp = Path("./ExecutorQueue.pickle")
    if bkp.exists():
      with open("ExecutorQueue.pickle","rb") as file:
        tasks = pickle.load(file)
    for task in tasks:
      ExecutorQueue.add_task(code=task['code'], edit_func=task['edit_func'], msg_id=task['msg_id'])
      print(f"Restored task [{task}] into queue")


  @staticmethod
  def init(threads=const.QUEUE_THREADS_AMOUNT, restore_queue=True):
    ExecutorQueue._code_queue = Queue()
    if restore_queue:
      ExecutorQueue.restore_queue()
    ExecutorQueue._executorPool = ThreadPoolExecutor(max_workers=threads)
    ExecutorQueue._actual_threads = threads
    for i in range(threads):
      ExecutorQueue._executorPool.submit(ExecutorQueue.process_task, ExecutorQueue._code_queue, i)


  @staticmethod
  def save_queue():
    tasks = []
    print(f"Queue size: {ExecutorQueue._code_queue._qsize()}")
    while not ExecutorQueue._code_queue.empty():
      qtask = ExecutorQueue._code_queue.get()
      tasks.append(qtask)
      print(f"Added task [{qtask}] to list for save")
    print("queue lock released, saving")
    with open("ExecutorQueue.pickle","wb") as file:
      pickle.dump(tasks, file)


  @staticmethod
  def shutdown(wait=True, cancel_futures=True, save_queue=True):
    ExecutorQueue._active = False
    print("Switched _active to False. Waiting 15 seconds for threads")
    time.sleep(15)
    print("Calling shutdown for ThreadPoolExecutor")
    ExecutorQueue._executorPool.shutdown(wait=wait, cancel_futures=cancel_futures)
    print("Shutdown finished")
    if save_queue:
      ExecutorQueue.save_queue()
      print("Queue saved")

