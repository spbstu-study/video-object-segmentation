import asyncio
import os
import tempfile
import time
import re
from datetime import datetime


TMPDIR = os.path.join(os.curdir, 'temp')


async def convert_mp4_to_jpg(video: bytes, progress_callback=None) -> str:
    if not os.path.exists(TMPDIR):
        os.mkdir(TMPDIR)

    subfolder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    current_temp_path = os.path.join(TMPDIR, subfolder)
    os.mkdir(current_temp_path)
    video_path = os.path.join(current_temp_path, 'input.mp4')

    with open(video_path, 'wb') as f:
        f.write(video)

    duration = await __get_video_duration(video_path)
    output_pattern = os.path.join(current_temp_path, 'frame_%05d.jpg')

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

    return current_temp_path


async def convert_jpg_to_mp4(input_dir: str, progress_callback=None) -> bytes:
    # Путь к временному файлу для финального видео
    output_video_path = os.path.join(input_dir, 'output.mp4')

    # Собираем список изображений
    image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.jpg')])

    if not image_files:
        raise ValueError("Нет изображений для конвертации.")

    input_pattern = os.path.join(input_dir, 'frame_%05d.jpg')

    input_video_path = os.path.join(input_dir, 'input.mp4')
    framerate = await __get_video_fps(input_video_path)

    # Запускаем ffmpeg для создания видео
    process = await asyncio.create_subprocess_exec(
        'ffmpeg',
        '-framerate', str(framerate),
        '-i', input_pattern,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        output_video_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE
    )

    last_update = time.time()
    reported_percent = -1

    while True:
        line = await process.stderr.readline()
        if not line:
            break

        decoded_line = line.decode('utf-8').strip()
        match = re.search(r'time=(\d+:\d+:\d+\.\d+)', decoded_line)
        if match:
            current_time = __parse_ffmpeg_time(match.group(1))
            total_duration = await __get_video_duration(output_video_path)  # Получаем длительность итогового видео
            percent = int((current_time / total_duration) * 100)

            now = time.time()
            if percent != reported_percent and (now - last_update) >= 1:
                reported_percent = percent
                last_update = now
                if progress_callback:
                    await progress_callback(min(percent, 100))

    await process.wait()

    if process.returncode != 0:
        raise RuntimeError("Ошибка при создании видео из изображений.")

    if progress_callback:
        await progress_callback(100)

    # Чтение готового видео в байты
    with open(output_video_path, 'rb') as f:
        video_bytes = f.read()

    return video_bytes


async def __get_video_fps(video_path: str) -> float:
    """Получение частоты кадров из видеофайла с помощью ffprobe."""
    process = await asyncio.create_subprocess_exec(
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"Ошибка при извлечении частоты кадров: {stderr.decode('utf-8')}")

    fps_str = stdout.decode('utf-8').strip()
    num, denom = map(int, fps_str.split('/'))
    return num / denom


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