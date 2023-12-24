from peewee import BooleanField, CharField, DateTimeField, IntegerField, Model, MySQLDatabase
from config import MYSQL_URL_MAIN
from playhouse.db_url import connect

database = connect(MYSQL_URL_MAIN, charset='utf8mb4')


class BaseModel(Model):
    class Meta:
        database = database