"""
ASGI config for drunkpoker project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

import django
import drunkpoker.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'drunkpoker.settings')
django.setup()

application = drunkpoker.routing.application
