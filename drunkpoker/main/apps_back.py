from django.apps import AppConfig
from django.utils.autoreload import autoreload_started
from pathlib import Path


def watch_extra_files(sender, *args, **kwargs):
    watch = sender.extra_files.add
    # List of file paths to watch
    path_elm = Path("c:/Users", "qbernard", "PycharmProjects", "drunkpoker", "drunkpoker", "main", "elm.js")
    path_index = Path("c:/Users", "qbernard", "PycharmProjects", "drunkpoker", "drunkpoker", "main", "index.html")
    print(path_elm.exists())
    watch_list = [path_elm, path_index]
    for file in watch_list:
        watch(file)



autoreload_started.connect(watch_extra_files)


class MainConfig(AppConfig):
    name = 'main'

