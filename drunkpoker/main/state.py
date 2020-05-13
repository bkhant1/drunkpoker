from drunkpoker.main.models import Table
from drunkpoker.main.engine import initial_state, is_table_empty
from channels.db import database_sync_to_async
import json


@database_sync_to_async
def get_table(name):
    try:
        return json.loads(Table.objects.get(name=name).state)
    except Table.DoesNotExist:
        return initial_state()


@database_sync_to_async
def set_table(name, state):
    try:
        the_table = Table.objects.get(name=name)
    except Table.DoesNotExist:
        the_table = Table(name=name)
    the_table.state = json.dumps(state)
    if is_table_empty(state):
        print("Deleting (or not saving) table as no player on it")
        the_table.delete()
    else:
        the_table.save()

