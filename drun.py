from executor_queue import ExecutorQueue
from docker_runner import init
import time

init()

code = """
from time import sleep
print('RUN #{n}')
print('hello world')
sleep({n})
print('bye')
"""

ExecutorQueue.init(restore_queue=False)

try:
    for i in range(15):
        ExecutorQueue.add_task(code.format(n=i+1), print, 0)

    time.sleep(20)
except KeyboardInterrupt:
    ExecutorQueue.shutdown(save_queue=False)