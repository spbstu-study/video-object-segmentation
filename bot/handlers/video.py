import asyncio
import os

import telegram
from telegram import Update
from telegram.error import TimedOut
from telegram.ext import ContextTypes, Application, MessageHandler, filters

import config
from bot.userdata import UserData
from neural_network.video_predict import video_predict
from utils.video import convert_mp4_to_jpg, convert_jpg_to_mp4, get_video_fps
from model import model


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
            try:
                await user_data.minor_message.edit_text(
                    config.message('minor.caption.processing')
                        .replace(
                        '<status>',
                        config.message('status.processing.prepare')
                            .replace('<pct>', str(pct))
                    )
                )
            except telegram.error.BadRequest:
                pass
        video = update.message.video
        video_file = await video.get_file()
        video_bytes = await video_file.download_as_bytearray()
        frame_dir = await convert_mp4_to_jpg(video_bytes, progress_callback=update_progress)
        input_video_path = os.path.join(frame_dir, 'input.mp4')
        processed_dir = f'{frame_dir}/processed/'

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.ai'))
        )

        if not os.path.exists(processed_dir):
            os.mkdir(processed_dir)
        await video_predict(model, f'{frame_dir}/*.jpg', processed_dir)

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
            .replace('<status>', config.message('status.processing.form'))
        )
        framerate = await get_video_fps(input_video_path)
        video_bytes = await convert_jpg_to_mp4(processed_dir, framerate, progress_callback=update_progress)

        retries = 5
        for attempt in range(retries):
            try:
                await update.message.chat.send_video(video_bytes)
                break
            except TimedOut:
                print(f"Timeout error, retrying ({attempt + 1}/{retries})...")
                await asyncio.sleep(2)

        await user_data.minor_message.edit_text(
            config.message('minor.caption.processing')
                .replace('<status>', config.message('status.processing.complete'))
        )
