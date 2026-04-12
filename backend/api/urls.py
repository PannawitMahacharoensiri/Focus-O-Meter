from django.urls import path
from .views import weather_data, attendance_data, tmd_data, data_in_daterange

urlpatterns = [
    path('weather/', weather_data),
    path('attendance/', attendance_data),
    path('tmd_data/', tmd_data),
    path('data_in_daterange/', data_in_daterange),
]