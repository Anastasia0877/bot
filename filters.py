from contextvars import ContextVar
from datetime import datetime
from aiogram.dispatcher.filters import BoundFilter
from aiogram.types import Message
from aiogram.dispatcher.handler import ctx_data
from models.user import User
from users import get_user
from aiogram.types import (
    InputFile,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ContentType,
    BotCommand,
)
from aiogram.dispatcher import FSMContext

class Admin(BoundFilter):
    key = "is_admin"

    def __init__(self, is_admin: bool):
        self.is_admin = is_admin

    async def check(self, message: Message):
        user = get_user(message.from_user.id)

        if not user:
            return False

        return user.is_admin == self.is_admin