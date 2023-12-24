from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, BigAutoField,IntegerField, Model, SqliteDatabase, ForeignKeyField, TextField

from models.base import BaseModel
from models.user import User



class Info(BaseModel):
    id = BigAutoField(primary_key=True)
    login = CharField(null=True, default=None)
    state = TextField(null=True, default=None)
    contacts = TextField(null=True, default=None)
    links_first = TextField(null=True, default=None)
    links_second = TextField(null=True, default=None)
    links_third = TextField(null=True, default=None)
    term = TextField(null=True, default=None)
    amount = TextField(null=True, default=None)
    notes = TextField(null=True, default=None)
    
    updated_notif = BooleanField(default=False)

    # free_period_used = BooleanField(default=False)
    # confirm_rules = BooleanField(default=False)
    # free_period = BooleanField(default=False)

    created_at = DateTimeField(default=lambda: datetime.utcnow())
    # blocked = BooleanField(default=False)

    def __repr__(self) -> str:
        return f"<Topup {self.user.id}>"

    class Meta:
        table_name = "infos"

# class UserChannel(BaseModel):
#     user_id = IntegerField()
#     channel_id = IntegerField()

#     def __repr__(self) -> str:
#         return f"<UserChannel {self.user_id} {self.channel_id}>"

#     class Meta:
#         table_name = "users_channels"
