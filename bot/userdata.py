from typing import Any

from telegram import Message

import config


class UserData:
    def __init__(self) -> None:
        self.minor_message: Message | None = None
        self.main_message: Message | None = None
