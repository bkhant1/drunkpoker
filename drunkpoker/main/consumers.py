from channels.db import database_sync_to_async
from channels.generic.http import AsyncHttpConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import drunkpoker.main.state as persistent_state
import drunkpoker.main.engine as engine
import os
import json


def get_host(headers):
    for key, value in headers:
        if key == b'host':
            return value.decode("utf-8")
    return ''


class BootstrapElm(AsyncHttpConsumer):

    async def handle(self, body):
        try:
            print(f'New player joining')
            await database_sync_to_async(self.scope["session"].save)()
            if "table_name" in self.scope["url_route"]["kwargs"]:
                pass
            with open(os.path.join(settings.ELM_APP_DIR, 'index.html')) as f:
                reply = f.read()
            await self.send_response(
                200,
                bytes(reply, encoding="utf-8"),
                headers=[
                    (b"Content-Type", b"text/html")
                ]
            )
        except Exception as e:
            print(e)


class ElmApp(AsyncHttpConsumer):

    async def handle(self, body):
        try:
            with open(os.path.join(settings.ELM_APP_DIR, 'elm.js')) as f:
                reply = f.read()
            await self.send_response(
                200,
                bytes(reply, encoding="utf-8"),
                headers=[
                    (b"Content-Type", b"text/javascript")
                ]
            )
        except Exception as e:
            print(e)


class PlayerActions(AsyncHttpConsumer):

    EVENT_TYPE_FROM_URL_ACTION = {
        "sit": engine.Event.PLAYER_SIT,
        "fold": engine.Event.FOLD,
        "nextGame": engine.Event.PLAYER_READY_FOR_NEXT_GAME,
        "check": engine.Event.CHECK,
        "call": engine.Event.CALL,
        "raise": engine.Event.RAISE,
        "showCards": engine.Event.SHOW_CARDS
    }

    def event_type(self):
        return self.EVENT_TYPE_FROM_URL_ACTION[
            self.scope["url_route"]["kwargs"]["action"]
        ]

    async def handle(self, body):
        """
        :param body: bytes for a valid json containing the action parameters
        """
        player_id = self.scope["session"].session_key

        print(
            f'Received action {self.scope["url_route"]["kwargs"]}, with body: {body}, player session id: ' +
            f'{player_id}')

        table_name = self.scope["url_route"]["kwargs"]["table_name"]
        table_type = self.scope["url_route"]["kwargs"]["table_type"]
        table_group_name = f'table_{table_type}_{table_name}'

        new_state = engine.process_event(
            await persistent_state.get_table(table_name, table_type),
            {
                "type": self.event_type(),
                "player_id": player_id,
                "parameters": json.loads(body)
            }
        )
        await persistent_state.set_table(
            table_name,
            table_type,
            new_state
        )
        await self.channel_layer.group_send(
            table_group_name,
            {
                'type': 'game_state_updated',
                'message': json.dumps(new_state)
            }
        )
        await self.send_response(
            200,
            bytes("Nothing to say, state will be updated through socket", encoding="utf-8"),
            headers=[
                (b"Content-Type", b"text/html")
            ]
        )


class StreamGameState(AsyncWebsocketConsumer):

    async def connect(self):
        player_id = self.scope["session"].session_key

        print(f'Player connected: {player_id}')

        self.table_name = self.scope['url_route']['kwargs']['table_name']
        self.table_type = self.scope['url_route']['kwargs']['table_type']
        self.table_group_name = f'table_{self.table_type}_{self.table_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.table_group_name,
            self.channel_name
        )

        await self.accept()
        await self.send(text_data=json.dumps(
            engine.strip_state_for_player(
                await persistent_state.get_table(self.table_name, self.table_type),
                player_id
            )
        ))

    async def disconnect(self, close_code):
        try:
            player_id = self.scope["cookies"]["sessionid"]

            print(f"Player leaving {player_id}")

            new_state = engine.process_event(
                await persistent_state.get_table(self.table_name, self.table_type),
                {
                    "type": engine.Event.PLAYER_LEAVE,
                    "player_id": player_id,
                }
            )
            await persistent_state.set_table(
                self.table_name,
                self.table_type,
                new_state
            )
            await self.channel_layer.group_send(
                self.table_group_name,
                {
                    'type': 'game_state_updated',
                    'message': json.dumps(new_state)
                }
            )
        except engine.EventRejected as e:
            print(e)

    async def game_state_updated(self, text_data):
        player_id = self.scope["cookies"]["sessionid"]
        print(f'Streaming state to {player_id}')

        state = json.loads(text_data["message"])
        new_state = engine.strip_state_for_player(state, player_id)

        text_state_to_send = json.dumps(new_state)
        print(text_state_to_send)
        await self.send(text_data=text_state_to_send)
