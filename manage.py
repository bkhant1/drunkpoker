#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from django.utils.autoreload import autoreload_started
from pathlib import Path


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drunkpoker.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


def watch_extra_files(sender, *args, **kwargs):
    watch = sender.extra_files.add
    # List of file paths to watch
    file_path = Path(os.path.realpath(__file__)).parts[0:-1]
    path_elm = Path(*file_path, "drunkpoker", "main", "frontend", "elm.js")
    path_index = Path(*file_path, "drunkpoker", "main", "frontend", "index.html")
    watch_list = [path_elm, path_index]
    for file in watch_list:
        watch(file)


if __name__ == '__main__':
    main()
