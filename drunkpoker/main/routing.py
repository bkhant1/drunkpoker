from django.urls import re_path
from . import consumers


http_urlpatterns = [
    re_path(r'(?P<table_type>normal|drinking)table/(?P<table_name>\w+)/actions/(?P<action>\w+)', consumers.PlayerActions.as_asgi()),
    re_path(r'^(?P<table_type>normal|drinking)table/(?P<table_name>\w+)', consumers.BootstrapElm.as_asgi()),
    re_path(r'^elm.js', consumers.ElmApp.as_asgi()),
    re_path(r'^$', consumers.BootstrapElm.as_asgi()),
]


websocket_patterns = [
    re_path(r'^ws/(?P<table_type>normal|drinking)table/(?P<table_name>\w+)', consumers.StreamGameState.as_asgi())
]
