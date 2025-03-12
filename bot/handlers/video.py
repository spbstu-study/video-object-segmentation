from telegram import Update
from telegram.ext import ContextTypes, Application, MessageHandler, filters

import config
from bot.userdata import UserData


class VideoHandler:
    def __init__(self, application: Application) -> None:
        application.add_handler(MessageHandler(filters.VIDEO, self.video_handler))

    async def video_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data: UserData = context.user_data

        user_data.minor_message = await update.message.chat.send_message(
            config.message('minor.caption.processing').replace('<status>', '(В зависимости от решения тут будет отображаться статус обработки)')
        )
