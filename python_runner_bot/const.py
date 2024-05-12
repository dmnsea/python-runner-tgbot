from os import getenv
from dotenv import load_dotenv

load_dotenv()

MAX_MESSAGE_TEXT_LENGTH = 4096
PYTHON_VERSIONS = getenv("PYTHON_VERSIONS", "3.8.10,3.10.12,3.12.3").split(",")
DEFAULT_IMAGE=f"python:{PYTHON_VERSIONS[-1]}"
CONTAINER_MEMORY_LIMIT_MB=int(getenv("CONTAINER_MEMORY_LIMIT_MB", "50"))
CONTAINER_EXECUTION_TIMEOUT=int(getenv("CONTAINER_TIMEOUT", "10"))
CONTAINER_STOP_TIMEOUT=int(getenv("CONTAINER_STOP_TIMEOUT", "5"))
# Used in ThreadPoolExecutor, default value of max_workers is min(32, os.cpu_count() + 4).
# https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
# Take into account DOCKER_CONTAINER_MEMORY_LIMIT and your server's resources to choose QUEUE_THREADS_AMOUNT value
SIMULTANEOUS_EXEC = int(getenv("SIMULTANEOUS_EXEC", "5"))

if __name__ == "__main__":
    print("version:", PYTHON_VERSIONS)
    print("default:", DEFAULT_IMAGE)
    print("mem limit:", CONTAINER_MEMORY_LIMIT_MB)
    print("exec timeout:", CONTAINER_EXECUTION_TIMEOUT)
    print("stop timeout:", CONTAINER_STOP_TIMEOUT)
    print("threads:", SIMULTANEOUS_EXEC)