from telegram import Update
from telegram.ext import ContextTypes, Application, MessageHandler, filters

import config
from bot.userdata import UserData
from utils.video import prepare_video


class VideoHandler:
    def __init__(self, application: Application) -> None:
        application.add_handler(MessageHandler(filters.VIDEO, self.video_handler))

    async def video_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_data: UserData = context.user_data

        user_data.minor_message = await update.message.chat.send_message(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.download'))
        )

        async def update_progress(pct):
            await user_data.minor_message.edit_text(
                config.message('minor.caption.processing')
                    .replace(
                    '<status>',
                    config.message('status.processing.prepare')
                        .replace('<pct>', str(pct))
                )
            )
        video = update.message.video
        video_file = await video.get_file()
        video_bytes = await video_file.download_as_bytearray()
        frame_dir = await prepare_video(video_bytes, progress_callback=update_progress)

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.ai'))
        )

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.upload'))
        )

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.complete'))
        )
