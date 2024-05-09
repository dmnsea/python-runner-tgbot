import asyncio
import logging
from os import getenv
import sys

from dumb_runner import run, explain
import localization as lc
import db

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types.bot_command import BotCommand
from aiogram.filters.command import Command

db.prepare_db()

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

##############################################################################
### Список команд с описаниями
# потом их можно использовать в конструкторе Command() для фильтрации сообщений
# а так же предоставить телеге, чтобы сказать какие команды есть у бота

СMD_START = BotCommand(command="start", description="Start using bot")
CMD_RUN = BotCommand(command="run", description="Run in group chats")
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
    exist = db.find_user(message.from_user.id)
    user_lang = None
    if exist:
        user_lang = exist["lang"]
    else:
        user_lang = "ru" if message.from_user.language_code == "ru" else "en"
        db.add_user(message.from_user.id, user_lang)
    await message.reply(
        lc.get("welcome",
               user_lang).format(username=message.from_user.full_name))


@dp.message(Command(CMD_HELP))
async def send_usage_hint(message: types.Message) -> None:
    lang = db.get_user_lang(message.from_user.id)
    manual = lc.get("usage_hint", lang).format(timeout_seconds="5 sec")
    await message.reply(manual)


@dp.message(Command(CMD_RUN))
async def process_group_chat_message(message: types.Message) -> None:
    await message.reply(process_message(message))


@dp.message(Command(CMD_SET_LANG))
async def change_locale(message: types.Message) -> None:
    # message.entities - список, где первой сущностью является команда.
    # данный обработчик работает по команде, т.е. эта сущность есть всегда
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
    lang = db.get_user_lang(message.from_user.id)
    cmd_len = message.entities[0].length
    arg = str(message.text)[cmd_len:].strip()
    raw_versions = ["3.10","3.12.3"]
    versions = list(map(lambda ver: f"- {ver}", raw_versions))
    if len(arg) == 0:
        user_ver = db.get_user_python(message.from_user.id) 
        hint = lc.get("python_versions",lang).format(
                user_version=user_ver,
                version_list="\n".join(versions), 
                latest=versions[-1]
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

# В самом конце, т.к. фактически является обработчиком для вообще всех сообщений (в лс)
@dp.message(F.chat.type == "private")  # без команды чисто для лс
async def process_private_message(message: types.Message) -> None:
    await message.reply(process_message(message))


##############################################################################
### ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def extract_code_entity(message: types.Message) -> str | None:
    if message.entities:
        pre = [e for e in message.entities if e.type == "pre"]
        if len(pre) == 0:
            return message.text
        pre = pre[
            0]  # берем только первый блок кода, он же наверняка единственный
        if message.text:
            return message.text[pre.offset:pre.offset + pre.length]
    else:
        return message.text


def process_message(message: types.Message) -> str:
    code = extract_code_entity(message)
    user_lang = "ru" if message.from_user.language_code == "ru" else "en"
    if code:
        result = run(code=code,
                     editor=message.edit_text,
                     msg_id=message.message_id,
                     filename=f"user_{message.from_user.id}.py")
        print("Dumb execution result:\n" + result)
        if "STDERR:\nTraceback" in result:
            explanation = explain(
                result, "ru", "3.11.4"
            )  # TODO надо получить код языка пользователя и передать вместо захардкоженного "ru", а так же брать версию из настроек пользователя
            result += "\n" + ('-' * 10) +\
            lc.get("ai_comment",user_lang) + explanation
        return result


##############################################################################
### ЗАПУСК
async def main() -> None:
    # And the run events dispatching
    bot = Bot(getenv("BOT_TOKEN", ""))
    # Сообщаем телеге какие команды у нас есть
    await bot.set_my_commands([СMD_START, CMD_RUN, CMD_HELP, CMD_SET_LANG, CMD_SET_PYTHON])
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
