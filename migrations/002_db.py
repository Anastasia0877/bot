"""Peewee migrations -- 002_db.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.python(func, *args, **kwargs)        # Run python code
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""
    
    migrator.add_fields(
        'users',

        pay_until=pw.DateTimeField(null=True),
        pay_forever=pw.BooleanField(default=False),
        balance=pw.IntegerField(default=0))

    @migrator.create_model
    class Info(pw.Model):
        id = pw.BigAutoField()
        login = pw.CharField(max_length=255, null=True)
        state = pw.TextField(null=True)
        contacts = pw.TextField(null=True)
        links_first = pw.TextField(null=True)
        links_second = pw.TextField(null=True)
        links_third = pw.TextField(null=True)
        term = pw.TextField(null=True)
        amount = pw.TextField(null=True)
        notes = pw.TextField(null=True)
        updated_notif = pw.TextField(default='False')
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "infos"

    @migrator.create_model
    class Query(pw.Model):
        id = pw.BigAutoField()
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'])
        info = pw.ForeignKeyField(column_name='info_id', field='id', model=migrator.orm['infos'])
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "query"

    @migrator.create_model
    class Setting(pw.Model):
        id = pw.BigAutoField()
        key = pw.TextField()
        value = pw.TextField(null=True)

        class Meta:
            table_name = "settings"

    @migrator.create_model
    class Topup(pw.Model):
        id = pw.BigAutoField()
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'])
        amount = pw.IntegerField()
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "topup"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.remove_fields('users', 'pay_until', 'pay_forever', 'balance')

    migrator.remove_model('topup')

    migrator.remove_model('settings')

    migrator.remove_model('query')

    migrator.remove_model('infos')
