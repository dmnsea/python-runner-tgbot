import asyncio
import logging
from os import getenv
import sys

# from dumb_runner import run, explain

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types.bot_command import BotCommand
from aiogram.filters.command import Command

from . import const
from . import database as db
from . import docker_runner
from . import localization as lc

#: Семафор для ограничения количества одновременно запускаемых контейнеров
exec_limit = asyncio.Semaphore(const.SIMULTANEOUS_EXEC)

#: Все обработчики должны быть закреплены за объектом Router или Dispatcher (прим. от aiogram)
dp = Dispatcher()

##############################################################################
### Список команд с описаниями
# потом их можно использовать в конструкторе Command() для фильтрации сообщений
# а так же предоставить телеге, чтобы сказать какие команды есть у бота

#: Описание команды старта бота
СMD_START = BotCommand(command="start", description="Start using bot")
#: Описание команды запуска кода
CMD_RUN = BotCommand(command="run", description="Run in group chats")
#: Описание команды для проверки оверхеда
CMD_TEST = BotCommand(command="test", description="Check run overhead")
#: Описание команды для отображения помощи
CMD_HELP = BotCommand(command="help", description="Usage hints")
#: Описание команды для смены локали
CMD_SET_LANG = BotCommand(command="set_lang", description="Switch locale")
#: Описание команды для смены используемой версии Python
CMD_SET_PYTHON = BotCommand(command="set_python",
description="Change Python version")

##############################################################################
### ОБРАБОТЧИКИ


@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
        Обработчик для "/start" - команды запуска

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message
    """
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    await message.reply(
        lc.get("welcome", lang).format(username=message.from_user.full_name))


@dp.message(Command(CMD_HELP))
async def send_usage_hint(message: types.Message) -> None:
    """
        Обработчик для "/help" - команды вызова справки по использованию бота

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message
    """
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    manual = lc.get("usage_hint", lang) \
        .format(timeout_seconds=f"{const.CONTAINER_EXECUTION_TIMEOUT} sec.")
    await message.reply(manual)


@dp.message(Command(CMD_SET_LANG))
async def change_locale(message: types.Message) -> None:
    """
        Обработчик для "/set_lang" - команды смены локализации для пользователя.
        Аргумент команды - код локализации, присутствующий среди представленных локализаций.

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message

        Команда является одним из типов сущностей, которые могут присутствовать в сообщении и aiogram в типе Message предоставляет информацию о присутствующих сущностях, в т.ч. позиция с которой сущность начинается и сколько символов занимает. За счет данной информации и извлекается аргумент команды.
    """
    # message.entities - список, где первой сущностью является команда.
    # данный обработчик работает по команде, т.е. эта сущность есть всегда
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    cmd_len = message.entities[0].length
    arg = str(message.text)[cmd_len:].strip()
    if len(arg) == 0:
        lang_list = lc.get_languages(lang)
        hint = lc.get("lang_options", lang).format(lang_list="\n".join(lang_list))
        await message.reply(hint)
        return
    codes = lc.get_lang_codes()
    if arg not in codes:
        not_available = lc.get("lang_not_available", lang).format(lang_code=arg)
        await message.reply(not_available)
        return
    db.update_lang(message.from_user.id, arg)
    success = lc.get("lang_changed", arg)
    await message.reply(success)


@dp.message(Command(CMD_SET_PYTHON))
async def change_python(message: types.Message) -> None:
    """
        Обработчик для "/set_python" - команды смены используемой по умолчанию версии Python
        Аргумент команды - номер версии Python, присутствующий среди указанных в модуле констант версий.

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message

        Команда является одним из типов сущностей, которые могут присутствовать в сообщении и aiogram в типе Message предоставляет информацию о присутствующих сущностях, в т.ч. позиция с которой сущность начинается и сколько символов занимает. За счет данной информации и извлекается аргумент команды.
    """
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    cmd_len = message.entities[0].length
    arg = str(message.text)[cmd_len:].strip()
    raw_versions = const.PYTHON_VERSIONS
    versions = list(map(lambda ver: f"- {ver}", raw_versions))
    if len(arg) == 0:
        user_ver = db.get_user_python(message.from_user.id) 
        hint = lc.get("python_versions",lang).format(
                user_version=user_ver,
                version_list="\n".join(versions), 
                latest=raw_versions[-1]
            )
        await message.reply(hint)
        return
    if arg not in raw_versions:
        not_available = lc.get("version_not_available", lang)
        await message.reply(not_available)
        return
    db.update_python(message.from_user.id, arg)
    success = lc.get("py_version_changed", lang).format(version=arg)
    await message.reply(success)


@dp.message(Command(CMD_TEST))
async def check_overhead(message: types.Message):
    """
        Обработчик для "/test" - команды запуска тестового контейнера с замером времени старта и остановки

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message
    """
    add_user_if_not_exist(message)
    async with exec_limit:
        result = await docker_runner.test_run()
        await message.reply(result)


# В самом конце, т.к. фактически является обработчиком для вообще всех сообщений (в лс)
@dp.message(Command(CMD_RUN))
@dp.message(F.chat.type == "private")  # без команды чисто для лс
async def process_code_message(message: types.Message) -> None:
    """
        Обработчик для "/run" - команды запуска указанного в сообщении кода. Команда предназначена для использования в групповых чатах.
        Аргумент команды - код на языке Python.
        Вместе с тем, является обработчиком для сообщений напрямую от пользователя (в "личном" чате). В таком случае весь текст сообщения практически считается кодом.

        В процессе работы вызывает функцию `extract_code`, которая призвана выделить из сообщения код.

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message

        Команда является одним из типов сущностей, которые могут присутствовать в сообщении и aiogram в типе Message предоставляет информацию о присутствующих сущностях, в т.ч. позиция с которой сущность начинается и сколько символов занимает. За счет данной информации и извлекается аргумент команды.
    """
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    code = extract_code(message)
    if code:
        reply = await message.reply(lc.get("code_queued", lang))
        async with exec_limit:
            await docker_runner.run_python_code(code=code, msg=reply, user_id=message.from_user.id)
    else:
        if message.text.startswith("/run"):
            await message.reply(lc.get("run_hint", lang))
        elif message.text.startswith("/"):
            await message.reply(lc.get("no_such_command", lang))
        else:
            await message.reply(lc.get("something_went_wrong", lang))


##############################################################################
### ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def add_user_if_not_exist(message: types.Message):
    """
        Проверка наличия пользователя в базе данных и его добавление при необходимости.
        Первоначально было частью обработчика команды "/start", но позднее вынесено в отдельную функцию и теперь используется во всех обработчиках.

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message

        Причина вынесения в отдельную функцию: в сценарии личного использования бота Telegram начинает с запуска посредством команды "/start" и поведение бота соответствует запланированному. Однако при использовании в групповых чатах их участники не проходят через этап "старта" бота, вследствие чего информация о пользователях не добавлялась в БД.
        Это в свою очередь приводило к тому, что в обработчики отдавались значения настроек "по умолчанию", а изменить их не представлялось возможным т.к. нельзя обновить значение в БД, которого еще нет.
    """
    exist = db.find_user(message.from_user.id)
    user_lang = None
    if exist:
        user_lang = exist["lang"]
    else:
        user_lang = "ru" if message.from_user.language_code == "ru" else "en"
        db.add_user(message.from_user.id, user_lang)


def extract_code(message: types.Message) -> str | None:
    """
        Простой обработчик сообщения, призванный извлечь код из текста сообщения.
        Ищет первую (предполагается, что она единственная) сущность типа "pre" (форматированный код), а при отсутствии таковой - кодом считается все сообщение после предварительного исключения из него команд бота.

        :param message: Полученное ботом сообщение
        :type message: aiogram.types.Message

        Форматированный код, как и команда, является одним из типов сущностей, которые могут присутствовать в сообщении и aiogram в типе Message предоставляет информацию о присутствующих сущностях, в т.ч. позиция с которой сущность начинается и сколько символов занимает. За счет данной информации извлекается содержимое блока кода, либо исключение команды из результата.
    """
    if message.entities:
        pre = [e for e in message.entities if e.type == "pre"]
        if len(pre) == 0:
            cmd = [e for e in message.entities if e.type == "bot_command"]
            cmd = cmd[0]
            return message.text[cmd.length:].strip()
        pre = pre[
            0]  # берем только первый блок кода, он же наверняка единственный
        if message.text:
            return message.text[pre.offset:pre.offset + pre.length].strip()
    else:
        return message.text


##############################################################################
### ЗАПУСК
async def main() -> None:
    """
        Асинхронная функция старта. Предварительно инициирует:
        - загрузку локализаций в память
        - подготовку базы данных
        - подготовку набора образов Docker (проверка наличия и загрузка при отсутствии таковых)
        
        Далее отправляет к Telegram список поддерживаемых ботом команд, после чего запускает самого бота в работу по механизму "long polling" - периодический опрос серверов Telegram на предмет сообщений для бота.

        Фреймворк aiogram имеет предопределенный обработчик для сигнала остановки (SIGINT), в результате которого завершается опрос серверов Telegram на предмет сообщений для бота и выполняются следующие инструкции - в частности, закрытие БД.
    """
    lc.init()
    db.prepare_db()
    docker_runner.init()
    bot = Bot(getenv("BOT_TOKEN", ""))
    const.BOT = bot
    # Сообщаем телеге какие команды у нас есть
    await bot.set_my_commands([СMD_START, CMD_RUN, CMD_HELP, CMD_SET_LANG, CMD_SET_PYTHON, CMD_TEST])
    await dp.start_polling(bot)
    db.close()


def start():
    """
    Синхронная функция, запускающая работу бота. Задает уровень логгирования и производит запуск асинхронной функции старта
    """
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

if __name__ == "__main__":
    start()
