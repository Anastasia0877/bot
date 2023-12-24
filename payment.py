from fastapi import FastAPI, Request, Response
from models.topup import Topup
from main import bot

from models.user import User

app = FastAPI()

@app.get("/")
async def root2(req: Request):
    return "work"

@app.post("/pay")
async def root(req: Request):
    data = await req.json()
    # req.query_params
    print()
    if data.get("LMI_SECRET_KEY") == "testpass":
        user_id = data.get("LMI_PAYMENT_DESC").split(" ")[-1]
        user_id = int(user_id)
        
        u = User.get(user_id)
        num = int(data.get("LMI_PAYMENT_AMOUNT"))
        u.balance += num
        u.save()
        Topup.create(amount=num, user=u)
        await bot.send_message(user_id, f"Ваш баланс пополнен на {num} рублей!\nВсего на балансе: {u.balance} рублей")
    return Response("YES")
