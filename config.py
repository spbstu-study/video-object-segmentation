import json


TOKEN = open('data/token.txt', encoding='utf-8').read()


def message(key: str) -> str:
    return __MESSAGES.get(key)


def picture(key: str):
    path = __PICTURES.get(key)
    if path is not None:
        return open(path, 'rb')


__MESSAGES = {}
__PICTURES = {}


def __read_messages():
    global __MESSAGES

    with open('data/messages.json', encoding='utf-8') as file:
        __MESSAGES = json.load(file)


def __read_pictures():
    global __PICTURES

    with open('data/images.json', encoding='utf-8') as file:
        __PICTURES = json.load(file)


__read_messages()
__read_pictures()