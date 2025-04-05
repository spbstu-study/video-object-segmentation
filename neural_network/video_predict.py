import glob
import os

import numpy as np
from skimage.io import imread, imsave
from skimage.transform import resize
from skimage import measure
from skimage.draw import polygon_perimeter
from skimage.morphology import dilation, disk


CLASSES = 8
SAMPLE_SIZE = (256, 256)


def video_predict(unet_like, video_frames_path_pattern, output_frames_path):
    """
    Args:
        unet_like: Переменная с нейронной сетью
        video_frames_path_pattern: Паттерн пути с исходными кадрами, например, *video-object-segmentation/videos/original_video/\*.jpg*
        output_frames_path: Путь к папке, куда сохранятся сегментированные кадры, например, *video-object-segmentation/videos/processed/*

    Returns:
        None
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

    frames = sorted(glob.glob(video_frames_path_pattern))

    for filename in frames:
        frame = imread(filename)
        sample = resize(frame, SAMPLE_SIZE)

        predict = unet_like.predict(sample.reshape((1,) + SAMPLE_SIZE + (3,)))
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

        imsave(f'{output_frames_path}{os.path.basename(filename)}', frame)


if __name__ == '__main__':
    from keras import models

    model = models.load_model('unet_model_v2.h5')
    input_path = 'temp/original/*.jpg'
    output_path = 'temp/processed/'
    video_predict(model, input_path, output_path)
