MAX_MESSAGE_TEXT_LENGTH = 4096
MAX_INLINE_QUERY_LENGTH = 256
DOCKER_DEFAULT_IMAGE="python:3.11.4"
DOCKER_CONTAINER_MEMORY_LIMIT_MB=50
DOCKER_CONTAINER_EXECUTION_TIMEOUT=10
DOCKER_CONTAINER_STOP_TIMEOUT=5
# Used in ThreadPoolExecutor, default value of max_workers is min(32, os.cpu_count() + 4).
# https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor
# Take into account DOCKER_CONTAINER_MEMORY_LIMIT and your server's resources to choose QUEUE_THREADS_AMOUNT value
QUEUE_THREADS_AMOUNT = 5