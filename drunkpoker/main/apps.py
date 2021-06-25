from django.apps import AppConfig
from django.utils.autoreload import autoreload_started


def my_watchdog(sender, **kwargs):
    sender.watch_file('C:\\Users\\qbernard\\PycharmProjects\\drunkpoker\\drunkpoker\\main\\frontend\elm.js')
    # to listen to multiple files, use watch_dir, e.g.
    # sender.watch_dir('/tmp/', '*.bar')


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        autoreload_started.connect(my_watchdog)