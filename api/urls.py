from django.urls import path
from .views import weather_data, attendance_data, tmd_data

urlpatterns = [
    path('weather/', weather_data),
    path('attendance/', attendance_data),
    path('tmd_data/', tmd_data),
]