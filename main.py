import asyncio
import logging
from os import getenv
import sys

from aiogram import Bot, Dispatcher, types
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


@dp.message(CommandStart)
async def command_start_handler(message: types.Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    await message.answer(f"Hello, {message.from_user.full_name}!")


@dp.message(Command(CMD_TEST))
async def message_handler(message: types.Message) -> any:
    try:
        if message:
            await message.answer(message.text)
        else:
            raise ValueError("Какое-то сообщение, которое не используется в обработчике)")
    except ValueError:
        await message.answer('empty message, write again')



##############################################################################
### ЗАПУСК
async def main() -> None:
    # And the run events dispatching
    bot = Bot(getenv("BOT_TOKEN", ""))
    # Сообщаем телеге какие команды у нас есть
    await bot.set_my_commands([
        СMD_START,
        CMD_TEST
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
