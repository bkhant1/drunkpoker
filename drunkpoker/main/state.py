from drunkpoker.main.models import Table
from drunkpoker.main.engine import initial_state
from channels.db import database_sync_to_async
import json


@database_sync_to_async
def get_table(name, table_type):
    try:
        return json.loads(Table.objects.get(name=f"{table_type}_{name}").state)
    except Table.DoesNotExist:
        return initial_state(table_type)


@database_sync_to_async
def set_table(name, table_type, state):
    try:
        the_table = Table.objects.get(name=f"{table_type}_{name}")
    except Table.DoesNotExist:
        the_table = Table(name=f"{table_type}_{name}")
    the_table.state = json.dumps(state)
    the_table.save()
