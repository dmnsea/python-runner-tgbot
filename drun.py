import asyncio
import docker_runner


text = docker_runner.run_python_code(
"""
from time import sleep
print('hello world')
#print([1,2,3].findFirst(4))
#sleep(15)
""",
    print,
    0,
    "my_super_code.py"
)

print(text)