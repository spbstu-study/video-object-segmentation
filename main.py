import logging

from telegram.ext import (
    Application,
    ApplicationBuilder, ContextTypes
)

from bot.handlers.video import VideoHandler
from config import TOKEN
from bot.handlers.start import StartHandler
from bot.userdata import UserData


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def main():
    context_types: ContextTypes = ContextTypes(user_data=UserData)

    application: Application = ApplicationBuilder().token(TOKEN).context_types(context_types).arbitrary_callback_data(True).build()

    StartHandler(application)
    VideoHandler(application)

    application.run_polling()


if __name__ == '__main__':
    main()
