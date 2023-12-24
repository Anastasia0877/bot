import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
# test bot
# BOT_TOKEN = os.environ["BOT_TOKEN"]
# CHAT_ID = int(os.environ["CHAT_ID"])
# MYSQL_URL = os.environ["MYSQL_URL"]
# MYSQL_URL_MAIN = os.environ["MYSQL_URL_MAIN"]
# CHANNEL_ID = os.environ["CHANNEL_ID"]

BOT_TOKEN = ""
MYSQL_URL = "mysql://root:root123@localhost/admin_db_jobs"
MYSQL_URL_MAIN = "mysql://root:root123@localhost/admin_db_main"
OPENAI_API_KEY = ""
MERCHANT_ID = 57776
ADMINS = [428800205, 678886913]
