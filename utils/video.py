import asyncio
import os
import tempfile
import time
import re


async def prepare_video(video: bytes, progress_callback=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, 'input.mp4')

        with open(video_path, 'wb') as f:
            f.write(video)

        duration = await __get_video_duration(video_path)
        output_pattern = os.path.join(tmpdir, 'frame_%05d.jpg')

        process = await asyncio.create_subprocess_exec(
            'ffmpeg',
            '-i', video_path,
            '-q:v', '2',
            output_pattern,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE
        )

        last_update = time.time()
        reported_percent = -1  # переменная инициализирована ЗАРАНЕЕ

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            decoded_line = line.decode('utf-8').strip()
            match = re.search(r'time=(\d+:\d+:\d+\.\d+)', decoded_line)
            if match:
                current_time = __parse_ffmpeg_time(match.group(1))
                percent = int((current_time / duration) * 100)

                now = time.time()
                if percent != reported_percent and (now - last_update) >= 1:
                    reported_percent = percent
                    last_update = now
                    if progress_callback:
                        await progress_callback(min(percent, 100))

        await process.wait()

        if process.returncode != 0:
            raise RuntimeError("Ошибка при разбиении видео на кадры.")

        if progress_callback:
            await progress_callback(100)

        return tmpdir


def __parse_ffmpeg_time(time_str: str) -> float:
    """Парсит строку формата 00:01:23.45 в секунды"""
    parts = time_str.split(':')
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s


async def __get_video_duration(video_path: str) -> float:
    """Получает длительность видео в секундах через ffprobe"""
    process = await asyncio.create_subprocess_exec(
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, _ = await process.communicate()
    duration = float(stdout.decode().strip())
    return duration