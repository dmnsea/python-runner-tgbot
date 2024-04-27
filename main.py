import asyncio
import logging
from os import getenv
import sys

from dumb_runner import run, explain

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types.bot_command import BotCommand
from aiogram.filters.command import Command

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

##############################################################################
### Список команд с описаниями
# потом их можно использовать в конструкторе Command() для фильтрации сообщений
# а так же предоставить телеге, чтобы сказать какие команды есть у бота

СMD_START = BotCommand(command="start", description="Start using bot")
CMD_TEST = BotCommand(command="test", description="test command")

##############################################################################
### ОБРАБОТЧИКИ


@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
  """
      This handler receives messages with `/start` command
      """
  await message.answer(f"Hello, {message.from_user.full_name}!")


def extract_code_entity(message: types.Message) -> str | None:
  if message.entities:
    print(message.entities)
    pre = [e for e in message.entities if e.type == "pre"]
    if len(pre) == 0:
      return message.text
    pre = pre[0]  # берем только первый блок кода, он же наверняка единственный
    if message.text:
      return message.text[pre.offset:pre.offset + pre.length]
  else:
    return message.text


def process_message(message: types.Message) -> str:
  code = extract_code_entity(message)
  print("Extracted code:\n" + code)
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
      result += "\n" + ('-' * 10) + "\nПояснение от ИИ:\n" + explanation
    return result


@dp.message(Command(CMD_TEST))  # /test
async def message_handler(message: types.Message) -> None:
  await message.answer(process_message(message))


@dp.message(F.chat.type == "private")  # без команды чисто для лс
async def process_private_message(message: types.Message) -> None:
  await message.answer(process_message(message))


##############################################################################
### ЗАПУСК
async def main() -> None:
  # And the run events dispatching
  bot = Bot(getenv("BOT_TOKEN", ""))
  # Сообщаем телеге какие команды у нас есть
  await bot.set_my_commands([СMD_START, CMD_TEST])
  await dp.start_polling(bot)


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, stream=sys.stdout)
  asyncio.run(main())
