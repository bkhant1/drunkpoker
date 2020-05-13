from channels.routing import ProtocolTypeRouter, URLRouter
from channels.staticfiles import StaticFilesWrapper
import drunkpoker.main.routing
from channels.sessions import SessionMiddlewareStack


application = ProtocolTypeRouter({
    "http": SessionMiddlewareStack(
        StaticFilesWrapper(
            URLRouter(
                drunkpoker.main.routing.http_urlpatterns
            )
        )
    ),
    "websocket": SessionMiddlewareStack(
        URLRouter(
            drunkpoker.main.routing.websocket_patterns
        )
    )
})
