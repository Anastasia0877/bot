from datetime import datetime

from peewee import BooleanField, CharField, DateTimeField, BigAutoField,IntegerField, Model, SqliteDatabase, ForeignKeyField

from models.base import BaseModel
from models.user import User



class Topup(BaseModel):
    id = BigAutoField(primary_key=True)
    user = ForeignKeyField(User, backref='topups')
    amount = IntegerField(null=False)
    # free_period_used = BooleanField(default=False)
    # confirm_rules = BooleanField(default=False)
    # free_period = BooleanField(default=False)

    created_at = DateTimeField(default=lambda: datetime.utcnow())
    # blocked = BooleanField(default=False)

    def __repr__(self) -> str:
        return f"<Topup {self.user.id}>"

    class Meta:
        table_name = "topup"

# class UserChannel(BaseModel):
#     user_id = IntegerField()
#     channel_id = IntegerField()

#     def __repr__(self) -> str:
#         return f"<UserChannel {self.user_id} {self.channel_id}>"

#     class Meta:
#         table_name = "users_channels"
