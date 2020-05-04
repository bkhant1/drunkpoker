from django.http import HttpResponse


def start_game(request, table_name=None):
    return HttpResponse(f"Welcome to drinking poker")
