from django.urls import path
from .views import (weather_data, attendance_data, tmd_data, daterange_based_rawdata, list_classroom,
                    classroom_based_rawdata, classroom_based_aggregated)

urlpatterns = [
    path('weather/', weather_data),
    path('attendance/', attendance_data),
    path('tmd_data/', tmd_data),
    path('daterange_based_rawdata/', daterange_based_rawdata),
    path('list_classrooms/', list_classroom),
    path('classroom_based_rawdata/', classroom_based_rawdata),
    path('classroom_based_aggregated/', classroom_based_aggregated),
]