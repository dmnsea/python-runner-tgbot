from os import getenv
from dotenv import load_dotenv

load_dotenv()

#: Максимальная длина сообщения
MAX_MESSAGE_TEXT_LENGTH = 4096
#: Используемые версии Python
PYTHON_VERSIONS = getenv("PYTHON_VERSIONS", "3.8.10,3.10.12,3.12.3").split(",")
#: Версия Python используемая по умолчанию для новых пользователей
DEFAULT_IMAGE=f"python:{PYTHON_VERSIONS[-1]}"
#: Ограничение оперативной памяти для контейнера
CONTAINER_MEMORY_LIMIT_MB=int(getenv("CONTAINER_MEMORY_LIMIT_MB", "50"))
#: Таймаут выполнения контейнера в секундах
CONTAINER_EXECUTION_TIMEOUT=int(getenv("CONTAINER_TIMEOUT", "10"))
#: Время ожидания остановки контейнера
CONTAINER_STOP_TIMEOUT=int(getenv("CONTAINER_STOP_TIMEOUT", "5"))
#: Количество одновременных запусков. Бот выполняет запуски асинхронно, поэтому необходимо установить количество одновременных запусков в соответствии с запланированным для бота количеством памяти
SIMULTANEOUS_EXEC = int(getenv("SIMULTANEOUS_EXEC", "5"))

if __name__ == "__main__":
    print("version:", PYTHON_VERSIONS)
    print("default:", DEFAULT_IMAGE)
    print("mem limit:", CONTAINER_MEMORY_LIMIT_MB)
    print("exec timeout:", CONTAINER_EXECUTION_TIMEOUT)
    print("stop timeout:", CONTAINER_STOP_TIMEOUT)
    print("threads:", SIMULTANEOUS_EXEC)