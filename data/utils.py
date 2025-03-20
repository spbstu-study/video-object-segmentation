import tensorflow as tf
import numpy as np
import glob
import os
from skimage import measure
from skimage.morphology import dilation, disk
from skimage.draw import polygon_perimeter
from skimage.io import imread, imsave
from skimage.transform import resize


# Константы для работы с данными
CLASSES = 8
COLORS = ['black', 'red', 'lime',
          'blue', 'orange', 'pink',
          'cyan', 'magenta']
SAMPLE_SIZE = (256, 256)
OUTPUT_SIZE = (1080, 1920)


def load_images(image, mask):
    image = tf.io.read_file(image)
    image = tf.io.decode_jpeg(image)
    image = tf.image.resize(image, OUTPUT_SIZE)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = image / 255.0

    mask = tf.io.read_file(mask)
    mask = tf.io.decode_png(mask)
    mask = tf.image.rgb_to_grayscale(mask)
    mask = tf.image.resize(mask, OUTPUT_SIZE)
    mask = tf.image.convert_image_dtype(mask, tf.float32)

    masks = []

    for i in range(CLASSES):
        masks.append(tf.where(tf.equal(mask, float(i)), 1.0, 0.0))

    masks = tf.stack(masks, axis=2)
    masks = tf.reshape(masks, OUTPUT_SIZE + (CLASSES,))

    return image, masks


def augmentate_images(image, masks):
    random_crop = tf.random.uniform((), 0.3, 1)
    image = tf.image.central_crop(image, random_crop)
    masks = tf.image.central_crop(masks, random_crop)

    random_flip = tf.random.uniform((), 0, 1)
    if random_flip >= 0.5:
        image = tf.image.flip_left_right(image)
        masks = tf.image.flip_left_right(masks)

    image = tf.image.resize(image, SAMPLE_SIZE)
    masks = tf.image.resize(masks, SAMPLE_SIZE)

    return image, masks


def prepare_dataset(images_path, masks_path, batch_size=8, augment=True):
    """
    Подготовка датасета для обучения и валидации

    Parameters:
    images_path (str): Путь к директории с изображениями
    masks_path (str): Путь к директории с масками
    batch_size (int): Размер батча
    augment (bool): Применять ли аугментацию данных

    Returns:
    tf.data.Dataset: Подготовленный датасет
    """
    images = sorted(glob.glob(images_path))
    masks = sorted(glob.glob(masks_path))

    images_dataset = tf.data.Dataset.from_tensor_slices(images)
    masks_dataset = tf.data.Dataset.from_tensor_slices(masks)

    dataset = tf.data.Dataset.zip((images_dataset, masks_dataset))

    dataset = dataset.map(load_images, num_parallel_calls=tf.data.AUTOTUNE)

    if augment:
        dataset = dataset.repeat(60)
        dataset = dataset.map(augmentate_images, num_parallel_calls=tf.data.AUTOTUNE)

    dataset = dataset.batch(batch_size)

    return dataset


def split_dataset(dataset, train_size=2000, test_size=100):
    """
    Разделение датасета на обучающий и тестовый

    Parameters:
    dataset (tf.data.Dataset): Исходный датасет
    train_size (int): Размер обучающего датасета
    test_size (int): Размер тестового датасета

    Returns:
    tuple: (train_dataset, test_dataset)
    """
    train_dataset = dataset.take(train_size).cache()
    test_dataset = dataset.skip(train_size).take(test_size).cache()

    return train_dataset, test_dataset


def visualize_predictions(model, frames_path, output_path):
    """
    Визуализация предсказаний модели на видеокадрах

    Parameters:
    model: Обученная модель
    frames_path (str): Путь к кадрам видео
    output_path (str): Путь для сохранения обработанных кадров
    """

    rgb_colors = [
        (0, 0, 0),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 165, 0),
        (255, 192, 203),
        (0, 255, 255),
        (255, 0, 255)
    ]

    frames = sorted(glob.glob(frames_path))

    for filename in frames:
        frame = imread(filename)
        sample = resize(frame, SAMPLE_SIZE)

        predict = model.predict(sample.reshape((1,) + SAMPLE_SIZE + (3,)))
        predict = predict.reshape(SAMPLE_SIZE + (CLASSES,))

        scale = frame.shape[0] / SAMPLE_SIZE[0], frame.shape[1] / SAMPLE_SIZE[1]

        frame = (frame / 1.5).astype(np.uint8)

        for channel in range(1, CLASSES):
            contour_overlay = np.zeros((frame.shape[0], frame.shape[1]))
            contours = measure.find_contours(np.array(predict[:, :, channel]))

            try:
                for contour in contours:
                    rr, cc = polygon_perimeter(contour[:, 0] * scale[0],
                                               contour[:, 1] * scale[1],
                                               shape=contour_overlay.shape)

                    contour_overlay[rr, cc] = 1

                contour_overlay = dilation(contour_overlay, disk(1))
                frame[contour_overlay == 1] = rgb_colors[channel]
            except:
                pass

        imsave(f'{output_path}/{os.path.basename(filename)}', frame)