from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/casino/crash/$", consumers.CrashConsumer.as_asgi()),
    re_path(r"ws/casino/mines/$", consumers.MinesConsumer.as_asgi()),
]
