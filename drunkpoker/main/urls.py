from django.urls import path

from . import views

urlpatterns = [
    path('table/<slug:table_name>', views.start_game, name='start-game'),
]
