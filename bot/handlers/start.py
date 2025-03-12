from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, ContextTypes, CommandHandler

import config
from bot.userdata import UserData

class StartHandler:
    def __init__(self, application: Application):
        application.add_handler(CommandHandler('start', self.start))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data: UserData = context.user_data

        user_data.main_message = await update.message.reply_photo(
            caption=config.message('main.caption.welcome'),
            photo=config.picture('main.welcome'),
        )
