from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, BigAutoField,IntegerField, Model, SqliteDatabase, ForeignKeyField, TextField

from models.base import BaseModel
from models.user import User



class Setting(BaseModel):
    id = BigAutoField(primary_key=True)
    key = TextField(null=False)
    value = TextField(null=True, default=None)

    def __repr__(self) -> str:
        return f"<Settings {self.key}:{self.value}>"

    class Meta:
        table_name = "settings"

# class UserChannel(BaseModel):
#     user_id = IntegerField()
#     channel_id = IntegerField()

#     def __repr__(self) -> str:
#         return f"<UserChannel {self.user_id} {self.channel_id}>"

#     class Meta:
#         table_name = "users_channels"
