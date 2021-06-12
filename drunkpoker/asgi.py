"""
ASGI config for drunkpoker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drunkpoker.settings')
django.setup()


# This module needs to be imported after the django setup, as it's got top level
# members for which initialization require the settings to be initialized.
import drunkpoker.routing

application = drunkpoker.routing.application
