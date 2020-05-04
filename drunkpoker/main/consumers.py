from channels.generic.http import AsyncHttpConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import drunkpoker.main.state as state
import drunkpoker.main.engine as engine
import os
import json


class WelcomePage(AsyncHttpConsumer):

    async def handle(self, body):
        await self.send_response(
            200,
            bytes(
                f"Welcome, go to <here>/table/<table_name_of_your_choice> and ask friends to join you if you have some",
                encoding="utf-8"),
            headers=[
                (b"Content-Type", b"text/plain")
            ]
        )


class ElmApp(AsyncHttpConsumer):

    async def handle(self, body):
        with open(os.path.join(settings.ELM_APP_DIR, 'elm.js')) as f:
            reply = f.read()
        await self.send_response(
            200,
            bytes(reply, encoding="utf-8"),
            headers=[
                (b"Content-Type", b"text/javascript")
            ]
        )


class JoinTable(AsyncHttpConsumer):

    async def handle(self, body):
        print(f'New player joining')
        self.scope["session"]["player_joined"] = True
        with open(os.path.join(settings.ELM_APP_DIR, 'index.html')) as f:
            reply = f.read()
        reply = reply.replace('<TABLE_NAME>', self.scope["url_route"]["kwargs"]["table_name"])
        await self.send_response(
            200,
            bytes(reply, encoding="utf-8"),
            headers=[
                (b"Content-Type", b"text/html")
            ]
        )


class PlayerActions(AsyncHttpConsumer):

    EVENT_TYPE_FROM_URL_ACTION = {
        "bet": engine.Event.PLAYER_SIT
    }

    def event_type(self):
        return self.EVENT_TYPE_FROM_URL_ACTION[
            self.scope["url_route"]["kwargs"]["action"]
        ]

    async def handle(self, body):
        """
        :param body: bytes for a valid json containing the action parameters
        """
        print(
            f'Received action {self.scope["url_route"]["kwargs"]}, with body: {body}, player session id: ' +
            f'{self.scope["session"].session_key}')

        table_name = self.scope["url_route"]["kwargs"]["table_name"]
        table_group_name = 'table_%s' % table_name
        import pdb; pdb.set_trace()
        new_state = engine.process_event(
            await state.get_table(table_name),
            {
                "type": self.event_type(),
                "player_id": self.scope["cookies"]["sessionid"],
                "parameters": json.loads(body)
            }
        )
        await state.set_table(
            table_name,
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
        self.table_name = self.scope['url_route']['kwargs']['table_name']
        self.table_group_name = 'table_%s' % self.table_name

        # Join room group
        await self.channel_layer.group_add(
            self.table_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def game_state_updated(self, text_data):
        await self.send(text_data=text_data["message"])
