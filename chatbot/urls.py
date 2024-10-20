from django.urls import path
from .views import ConvertData

urlpatterns = [
    path('convertdata/', ConvertData.as_view(), name='convertdata'),
]