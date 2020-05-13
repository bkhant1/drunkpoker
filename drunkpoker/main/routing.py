from django.urls import re_path
from . import consumers


http_urlpatterns = [
    re_path(r'table/(?P<table_name>\w+)/actions/(?P<action>\w+)', consumers.PlayerActions),
    re_path(r'^table/(?P<table_name>\w+)', consumers.JoinTable),
    re_path(r'^elm.js', consumers.ElmApp),
    re_path(r'^$', consumers.WelcomePage),
]


websocket_patterns = [
    re_path(r'^ws/table/(?P<table_name>\w+)', consumers.StreamGameState)
]
