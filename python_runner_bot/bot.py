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

exec_limit = asyncio.Semaphore(const.SIMULTANEOUS_EXEC)

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

##############################################################################
### Список команд с описаниями
# потом их можно использовать в конструкторе Command() для фильтрации сообщений
# а так же предоставить телеге, чтобы сказать какие команды есть у бота

СMD_START = BotCommand(command="start", description="Start using bot")
CMD_RUN = BotCommand(command="run", description="Run in group chats")
CMD_TEST = BotCommand(command="test", description="Check run overhead")
CMD_HELP = BotCommand(command="help", description="Usage hints")
CMD_SET_LANG = BotCommand(command="set_lang", description="Switch locale")
CMD_SET_PYTHON = BotCommand(command="set_python",
                            description="Change Python version")

##############################################################################
### ОБРАБОТЧИКИ


@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    await message.reply(
        lc.get("welcome", lang).format(username=message.from_user.full_name))


@dp.message(Command(CMD_HELP))
async def send_usage_hint(message: types.Message) -> None:
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    manual = lc.get("usage_hint", lang) \
        .format(timeout_seconds=f"{const.CONTAINER_EXECUTION_TIMEOUT} sec.")
    await message.reply(manual)


@dp.message(Command(CMD_SET_LANG))
async def change_locale(message: types.Message) -> None:
    # message.entities - список, где первой сущностью является команда.
    # данный обработчик работает по команде, т.е. эта сущность есть всегда
    add_user_if_not_exist(message)
    lang = db.get_user_lang(message.from_user.id)
    cmd_len = message.entities[0].length
    arg = str(message.text)[cmd_len:].strip()
    if len(arg) == 0:
        lang_list = lc.get_languages(lang)
        hint = lc.get("lang_options",
                      lang).format(lang_list="\n".join(lang_list))
        await message.reply(hint)
        return
    codes = lc.get_lang_codes()
    if arg not in codes:
        not_available = lc.get("lang_not_available",
                               lang).format(lang_code=arg)
        await message.reply(not_available)
        return
    db.update_lang(message.from_user.id, arg)
    success = lc.get("lang_changed", arg)
    await message.reply(success)


@dp.message(Command(CMD_SET_PYTHON))
async def change_python(message: types.Message) -> None:
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
    add_user_if_not_exist(message)
    async with exec_limit:
        result = await docker_runner.test_run()
        await message.reply(result)

# В самом конце, т.к. фактически является обработчиком для вообще всех сообщений (в лс)
@dp.message(Command(CMD_RUN))
@dp.message(F.chat.type == "private")  # без команды чисто для лс
async def process_code_message(message: types.Message) -> None:
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
    exist = db.find_user(message.from_user.id)
    user_lang = None
    if exist:
        user_lang = exist["lang"]
    else:
        user_lang = "ru" if message.from_user.language_code == "ru" else "en"
        db.add_user(message.from_user.id, user_lang)

def extract_code(message: types.Message) -> str | None:
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
    db.prepare_db()
    docker_runner.init()
    # And the run events dispatching
    bot = Bot(getenv("BOT_TOKEN", ""))
    const.BOT = bot
    # Сообщаем телеге какие команды у нас есть
    await bot.set_my_commands([СMD_START, CMD_RUN, CMD_HELP, CMD_SET_LANG, CMD_SET_PYTHON, CMD_TEST])
    await dp.start_polling(bot)
    db.close()


def start():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

if __name__ == "__main__":
    start()
