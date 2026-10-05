from django.urls import path

from . import views

app_name = 'integrations'

urlpatterns = [
    path('', views.demo_hub, name='demo_hub'),
]
