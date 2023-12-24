import asyncio
from datetime import datetime, timedelta
from itertools import cycle
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import random
from string import ascii_lowercase
import threading
import time
import traceback
from typing import List
from playhouse.shortcuts import model_to_dict
from aiogram import Bot, Dispatcher, executor, types
from aiogram import types
import aiogram
import requests
from config import (
    ADMINS,
    BOT_TOKEN,
    MERCHANT_ID,
    MYSQL_URL,
    OPENAI_API_KEY
)
from filters import Admin
from middlewares import UsersMiddleware
from aiogram.dispatcher import FSMContext
import csv
from aiogram.utils.exceptions import ChatNotFound
from aiogram.utils.deep_linking import get_start_link
from aiogram.types import ContentType

from aiogram.types import (
    InputFile,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    ContentType,
    BotCommand,
)
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from models.info import Info
from models.query import Query
from models.settings import Setting
from models.topup import Topup
from models.user import User
from users import count_users, delete_user, get_user, get_user_ids, get_users
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.date import DateTrigger
from aiogram.utils.exceptions import BotBlocked
from aiogram.utils.callback_data import CallbackData
from aiohttp.helpers import sentinel
import aiohttp

import openai
openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


def create_timed_rotating_log(path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = TimedRotatingFileHandler(
        "logs/" + path, when="d", interval=1, backupCount=5
    )
    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler())

    return logger


logger = create_timed_rotating_log("logs.log")

jobstores = {"default": SQLAlchemyJobStore(url=MYSQL_URL)}
scheduler = AsyncIOScheduler(jobstores=jobstores)
storage = MemoryStorage()
bot = Bot(BOT_TOKEN, parse_mode="html")
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(UsersMiddleware())
# dp.filters_factory.bind(BlockedFilter)
dp.filters_factory.bind(Admin)

@dp.message_handler(commands=["id"], state="*")
async def get_id(message: types.Message):
    await message.answer(message.from_user.id)

@dp.message_handler(commands=["start"], state="*")
async def process_update(message: Message, state: FSMContext):
    await state.finish()
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Пополнить баланс", callback_data="add_money"),
        InlineKeyboardButton("Пополнить подписку", callback_data="pay_sub"),
        InlineKeyboardButton("Диалог с ИИ", callback_data="call_ai"),
        InlineKeyboardButton("Сделать запрос", callback_data="make_query"),
    )
    ad = Setting.get_or_none(key="ad")
    if ad is None:
        await message.answer("Меню", reply_markup=kb)
    else:
        await message.answer(f"Меню\n\n{ad.value}", reply_markup=kb)

class MakeQueryStates(StatesGroup):
    fieldname = State()
    value = State()
    show_full = State()
    full_choice = State()

# class InfoField:
#     def __init__(self, db_field, name):
#         self.db_field = db_field
#         self.name = name

info_fields = {
    "id": "ID",
    "login": "Логин",
    "state": "Данные",
    "contacts": "Контакты",
    "links_first": "Ссылки №1",
    "links_second": "Ссылки №2",
    "links_third": "Ссылки №3",
    "term": "Термин",
    "amount": "Покупки",
    "notes": "Записка"
}

query_field_cb = CallbackData("query_field", "field")

@dp.callback_query_handler(text="make_query")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await MakeQueryStates.fieldname.set()
    kb = InlineKeyboardMarkup(row_width=2).add(
        *[InlineKeyboardButton(info_fields[field], callback_data=query_field_cb.new(field)) for field in info_fields.keys()],
        get_cancel_btn()
    )
    await call.message.answer("Выберите по какому полю производить поиск информации", reply_markup=kb)


@dp.callback_query_handler(query_field_cb.filter(), state=MakeQueryStates.fieldname)
async def process_update(call: CallbackQuery, state: FSMContext, callback_data: dict):
    await call.answer()
    await MakeQueryStates.value.set()
    field = callback_data["field"]
    await state.update_data(field=field)
    await call.message.answer("Отправьте текст который содержится в этом поле", reply_markup=get_cancel_kb())

@dp.message_handler(state=MakeQueryStates.value)
async def process_update(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data["field"]
    res = Info.select().where(exec(f"Info.{field} ** \"{message.text}\"")).execute()
    if len(res) == 0:
        await message.answer(f"По вашему запросу ничего не найдено. Попробуйте ввести другое значение", reply_markup=get_cancel_kb())
    else:
        await MakeQueryStates.show_full.set()
        info = model_to_dict(res[0])
        await state.update_data(info_id=res[0].id)
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Получить полную информацию", callback_data="get_all_info")
        )
        await message.answer(f"По вашему запросу найдено {len(res)} результатов. Первый из них:\n\n"+"\n".join([f"{info_fields[field]}: {info[field]}" for field in ["id", "login"]]), reply_markup=kb)

@dp.callback_query_handler(text="get_all_info", state=MakeQueryStates.show_full)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    u = User.get(call.from_user.id)

    if not u.pay_forever:
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Оплатить подписку", callback_data="pay_sub"),
            InlineKeyboardButton("Оплатить запрос (10 рублей)", callback_data="pay_query"),
            get_cancel_btn()
        )
        await MakeQueryStates.full_choice.set()
        if u.pay_until:
            if u.pay_until < datetime.now():
                await MakeQueryStates.full_choice.set()
                await call.message.answer("У вас кончилась подписка. Вы можете продолжить подписку или купить доступ к этому запросу сейчас.", reply_markup=kb)
                return
        else:
            q = Query.select().where(Query.user == u).count()
            print(q)
            max_amount = Setting.get_or_none(key="query_max_amount")
            if max_amount:
                if q >= int(max_amount.value):
                    await call.message.answer("Вы превысили лимит бесплатных запросов. Вы можете продолжить подписку или купить доступ к этому запросу сейчас.", reply_markup=kb)
                    return
    info_id = (await state.get_data())["info_id"]
    await state.finish()
    info = Info.get(info_id)
    Query.create(user=u, info=info)
    info = model_to_dict(info)
    await call.message.answer("\n".join([f"{info_fields[field]}: {info[field]}" for field in info_fields]))
    await call.message.answer("Для возвращения в главное меню: /start")

@dp.callback_query_handler(text="pay_query", state=MakeQueryStates.full_choice)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    u = User.get(call.from_user.id)
    if u.balance < 10:
        await state.finish()
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Пополнить баланс", callback_data="add_money"),
            InlineKeyboardButton("Оплатить подписку", callback_data="pay_sub"),
        )
        await call.message.answer("У вас недостаточно денег на балансе", reply_markup=kb)
    else:
        u.balance -= 10
        u.pay_forever = True
        u.save()
        info_id = (await state.get_data())["info_id"]
        await state.finish()
        info = Info.get(info_id)
        Query.create(user=u, info=info)
        info = model_to_dict(info)
        await call.message.answer("\n".join([f"{info_fields[field]}: {info[field]}" for field in info_fields]))
        await call.message.answer("Для возвращения в главное меню: /start")

class PaySubStates(StatesGroup):
    sub_menu = State()

@dp.callback_query_handler(text="pay_sub")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await pay_sub(call, state)

@dp.callback_query_handler(text="pay_sub", state=MakeQueryStates.show_full)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await pay_sub(call, state)



async def pay_sub(call: CallbackQuery, state: FSMContext):
    u = User.get(call.from_user.id)
    text = "неизвестно"
    if u.pay_forever:
        text = "бесконечная подписка"
    else:
        if u.pay_until is None:
            text = "нет подписки"
        else:
            if u.pay_until > datetime.now():
                text = u.pay_until - datetime.now()
            else:
                text = "у вас кончилась подписка"
    kb = InlineKeyboardMarkup(row_width=1)
    if not u.pay_forever:
        kb.add(
            InlineKeyboardButton("Безлимит (500 рублей)", callback_data="pay_unlimit"),
        )
    kb.add(
        get_cancel_btn()
    )
    if u.pay_forever:
        await call.message.answer(f"Ваш баланс: {u.balance} рублей\nДо конца подписки осталось: {text}", reply_markup=kb)
    else:
        await call.message.answer(f"Ваш баланс: {u.balance} рублей\nДо конца подписки осталось: {text}\nВыберите тариф для пополнения", reply_markup=kb)

@dp.callback_query_handler(text="pay_unlimit")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    u = User.get(call.from_user.id)
    if u.balance < 500:
        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton("Пополнить баланс", callback_data="add_money"),
            InlineKeyboardButton("Оплатить подписку сразу", callback_data="pay_now"),
        )
        await call.message.answer("У вас недостаточно денег на балансе", reply_markup=kb)
    else:
        u.balance -= 500
        u.pay_forever = True
        u.save()
        await call.message.answer("Вы успешно приобрели тариф за счёт баланса! Нажмите /start для выхода в главное меню")
    
@dp.callback_query_handler(text="pay_now")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    num = 500
    data = {
        "LMI_PAYEE_PURSE": MERCHANT_ID,
        "LMI_PAYMENT_AMOUNT": num,
        "LMI_PAYMENT_DESC": f"Пополнение на {num} рублей для пользователя с ID {call.from_user.id}",
        "LMI_PAYMENT_NO": int(time.time())
    }
    u = "https://seller.pokupo.ru/api/ru/payment/merchant?" + urllib.parse.urlencode(data)
    await call.message.answer(f"Ссылка для оплаты: {u}")
    # await asyncio.sleep(2)
    # u = User.get(call.message.from_user.id)
    # u.balance += 500
    # u.save()
    # num = 500
    # Topup.create(amount=num, user=u)
    # await call.message.answer(f"Ваш баланс пополнен на {num} рублей!\nВсего на балансе: {u.balance} рублей")

class AddMoneyStates(StatesGroup):
    amount = State()

@dp.callback_query_handler(text="cancel", state="*")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()
    await call.message.answer("Отменено. Нажмите /start чтобы начать снова")

def get_cancel_btn():
    return InlineKeyboardButton("Отмена", callback_data="cancel")

def get_cancel_kb():
    return InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("Отмена", callback_data="cancel"))

import urllib.parse

@dp.callback_query_handler(text="add_money")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await AddMoneyStates.amount.set()
    await call.message.answer("На сколько рублей вы хотите пополнить баланс?", reply_markup=get_cancel_kb())

@dp.message_handler(state=AddMoneyStates.amount)
async def process_update(message: Message, state: FSMContext):
    num = message.text
    if not num.isdecimal():
        await message.answer("Это не число")
        return
    num = int(num)
    if num < 0:
        await message.answer("Укажите число больше 0")
        return
    await state.finish()
    data = {
        "LMI_PAYEE_PURSE": MERCHANT_ID,
        "LMI_PAYMENT_AMOUNT": num,
        "LMI_PAYMENT_DESC": f"Пополнение на {num} рублей для пользователя с ID {message.from_user.id}",
        "LMI_PAYMENT_NO": int(time.time())
    }
    u = "https://seller.pokupo.ru/api/ru/payment/merchant?" + urllib.parse.urlencode(data)
    await message.answer(f"Ссылка для оплаты: {u}")


class TalkAIStates(StatesGroup):
    talk = State()

@dp.callback_query_handler(text="call_ai")
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("Вы приступили к разговору с ИИ. Чтобы выйти напишите /start")
    await TalkAIStates.talk.set()

@dp.message_handler(state=TalkAIStates.talk)
async def process_update(message: Message, state: FSMContext):
    msg = await message.answer("ИИ думает...")
    async with state.proxy() as data:
        messages = data.get("messages")
        if messages is None:
            data["messages"] = []
        data["messages"].append(
            {"role": "user", "content": message.text},
        )
        chat = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo", messages=data["messages"]
        )
        reply = chat.choices[0].message.content
        data["messages"].append({"role": "assistant", "content": reply})
        await msg.edit_text(f"Ответ: {reply}")

@dp.message_handler(commands=["admin", "adm"], is_admin=True)
async def process_update(message: Message, state: FSMContext):
    await send_admin(message)

import peewee

async def send_admin(message: Message):
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Изменить рекламу", callback_data="change_ad"),
        InlineKeyboardButton("Изменить количество запросов", callback_data="change_query_amount"),
        InlineKeyboardButton("Установить цель", callback_data="change_goal"),
        InlineKeyboardButton("Добавить анкету", callback_data="add_people"),
    )
    amount = Topup.select(peewee.fn.SUM(Topup.amount)).scalar()
    if amount is None:
        amount = 0
    goal = Setting.get_or_none(key="goal")
    if goal is None:
        goal = 0
        text = ""
    else:
        goal = int(goal)
        if amount >= goal:
            text = " (собрано)"
        else:
            text = ""
    await message.answer(f"Админ-панель\n\nВсего собрано: {amount}/{goal} рублей{text}", reply_markup=kb)

class AddPeopleStates(StatesGroup):
    text = State()

@dp.callback_query_handler(text="add_people", is_admin=True)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await AddPeopleStates.text.set()
    l = list(info_fields.values())
    l.remove("ID")
    await call.message.answer("Отправьте анкету в таком формате:\n"+"\n".join(["{" + str(field) + "}" for field in l]))

@dp.message_handler(state=AddPeopleStates.text, is_admin=True)
async def process_update(message: Message, state: FSMContext):
    l = list(info_fields.values())
    l.remove("ID")
    l = len(l)
    texts = message.text.split("\n")
    if len(texts) != l:
        await message.answer("Количество полей не соответствует шаблону")
        return
    await state.finish()
    fields = list(info_fields.values())
    fields.remove("ID")
    Info.create(**{fields[i]: texts[i] for i in range(len(fields))})
    await message.answer("Успешно создано!")

class ChangeAdStates(StatesGroup):
    text = State()

@dp.callback_query_handler(text="change_ad", is_admin=True)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await ChangeAdStates.text.set()
    await call.message.answer("Отправьте сообщение с текстом рекламы")

@dp.message_handler(state=ChangeAdStates.text, is_admin=True)
async def process_update(message: Message, state: FSMContext):
    await state.finish()
    Setting.get_or_create(key="ad", value=message.text)
    await message.answer("Успешно изменено!")
    await send_admin(message)

class ChangeQueryAmountStates(StatesGroup):
    amount = State()

@dp.callback_query_handler(text="change_query_amount", is_admin=True)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await ChangeQueryAmountStates.amount.set()
    await call.message.answer("Отправьте число запросов")

@dp.message_handler(state=ChangeQueryAmountStates.amount, is_admin=True)
async def process_update(message: Message, state: FSMContext):
    await state.finish()
    num = message.text
    if not num.isdecimal():
        await message.answer("Это не число")
        return
    num = int(num)
    if num <= 0:
        await message.answer("Укажите число больше или равно 0")
        return
    Setting.get_or_create(key="query_max_amount", value=str(num))
    await message.answer("Успешно изменено!")
    await send_admin(message)

class ChangeGoalStates(StatesGroup):
    amount = State()

@dp.callback_query_handler(text="change_goal", is_admin=True)
async def process_update(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await ChangeGoalStates.amount.set()
    await call.message.answer("Отправьте необходимое число")

@dp.message_handler(state=ChangeGoalStates.amount, is_admin=True)
async def process_update(message: Message, state: FSMContext):
    await state.finish()
    num = message.text
    if not num.isdecimal():
        await message.answer("Это не число")
        return
    num = int(num)
    if num <= 0:
        await message.answer("Укажите число больше или равно 0")
        return
    Setting.get_or_create(key="goal", value=str(num))
    await message.answer("Успешно изменено!")
    await send_admin(message)

async def make_notif():
    res=Info.select().where(Info.updated_notif == True).execute()
    for info in res:
        info.updated_notif = False
        info.save()
    for info in res:
        user_ids = set()
        for query in info.queries_info:
            user_id = query.user.id
            if user_id in user_ids:
                continue
            user_ids.add(user_id)
            info = model_to_dict(info)
            await bot.send_message(user_id, "Ваш запрос был обновлен:\n"+"\n".join([f"{info_fields[field]}: {info[field]}" for field in info_fields]))

# if scheduler.get_job("notif") is None:
#     scheduler.add_job(make_notif, trigger="interval", seconds=30, id="notif")

if __name__ == "__main__":
    scheduler.start()
    executor.start_polling(dp, skip_updates=True)