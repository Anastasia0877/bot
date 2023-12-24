from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, BigAutoField,IntegerField, Model, SqliteDatabase, AutoField

from models.base import BaseModel



class User(BaseModel):
    id = BigAutoField(primary_key=True)
    username = CharField(default=None, null=True)
    is_admin = BooleanField(default=False)
    # free_period_used = BooleanField(default=False)
    # confirm_rules = BooleanField(default=False)
    # free_period = BooleanField(default=False)
    pay_until = DateTimeField(null=True, default=None)
    pay_forever = BooleanField(default=False)
    balance = IntegerField(default=0, null=False)

    created_at = DateTimeField(default=lambda: datetime.utcnow())
    # blocked = BooleanField(default=False)

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    class Meta:
        table_name = "users"

# class UserChannel(BaseModel):
#     user_id = IntegerField()
#     channel_id = IntegerField()

#     def __repr__(self) -> str:
#         return f"<UserChannel {self.user_id} {self.channel_id}>"

#     class Meta:
#         table_name = "users_channels"
