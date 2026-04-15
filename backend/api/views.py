"""
API views for retrieving weather and attendance data.

This module provides read-only endpoints using Django REST Framework.
Each endpoint supports optional pagination through query parameters:

- limit: number of records to return
- offset: starting index of records

Database sources:
- Default database: inclass weather data
- 'people_db' database: attendance and TMD weather data
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import ProjectInclassWeather, ProjectInclassAttendance, Tmd_weather
from datetime import timedelta
from django.db.models import Avg, Max, Min, Count, Q

@extend_schema(
    parameters=[
        OpenApiParameter(name='limit', description='Number of records', required=False, type=int),
        OpenApiParameter(name='offset', description='Start position', required=False, type=int),
        OpenApiParameter(name='classroom', description='Name of the course', required=False, type=str),
    ]
)
@api_view(['GET'])
def weather_data(request):
    limit = request.GET.get('limit')
    offset = request.GET.get('offset')
    classroom = request.GET.get('classroom')

    data = ProjectInclassWeather.objects.all().values()
    try:
        # Filter data
        if classroom:
            data = data.filter(classroom=classroom)

        # Slicing data
        if offset:
            data = data[int(offset):]
        if limit:
            data = data[:int(limit)]
    except ValueError:
        return Response({"error": "limit/offset must be numbers and classroom must be string"}, status=400)

    return Response(list(data))


@extend_schema(
    parameters=[
        OpenApiParameter(name='limit', description='Number of records', required=False, type=int),
        OpenApiParameter(name='offset', description='Start position', required=False, type=int),
        OpenApiParameter(name='classroom', description='Name of the course', required=False, type=str),
    ]
)
@api_view(['GET'])
def attendance_data(request):
    limit = request.GET.get('limit')
    offset = request.GET.get('offset')
    classroom = request.GET.get('classroom')

    data = ProjectInclassAttendance.objects.using('people_db').all().values()
    
    try:
        # Filter data 
        if classroom:
            data = data.filter(classroom=classroom)

        # Slicing data
        if offset:
            data = data[int(offset):]
        if limit:
            data = data[:int(limit)]
    except ValueError:
        return Response({"error": "Limit/Offset must be numbers and classroom must be string."}, status=400)

    return Response(list(data))


@extend_schema(
    parameters=[
        OpenApiParameter(name='limit', description='Number of records', required=False, type=int),
        OpenApiParameter(name='offset', description='Start position', required=False, type=int),
    ]
)
@api_view(['GET'])
def tmd_data(request):
    limit = request.GET.get('limit')
    offset = request.GET.get('offset')

    data = Tmd_weather.objects.using('people_db').all().values()
    try:
        if offset:
            data = data[int(offset):]
        if limit:
            data = data[:int(limit)]
    except ValueError:
        return Response({"error": "Limit/Offset must be numbers."}, status=400)

    return Response(list(data))

@extend_schema(
    description="Get unique classrooms from both weather and attendance tables"
)
@api_view(['GET'])
def list_classroom(request):
    weather_classes = ProjectInclassWeather.objects.values_list('classroom', flat=True)
    attendance_classes = ProjectInclassAttendance.objects.using('people_db').values_list('classroom', flat=True)

    # Remove empty values
    weather_classes = {c for c in weather_classes if c}
    attendance_classes = {c for c in attendance_classes if c}

    # All classrooms
    all_classes = weather_classes | attendance_classes

    # Common classrooms
    common_classes = weather_classes & attendance_classes

    return Response([{
        "all_classrooms": sorted(all_classes),
        "common_classrooms": sorted(common_classes)
    }])


@extend_schema(
    parameters=[
        OpenApiParameter(name='classroom', description='Name of the course', required=True, type=str),
    ]
)
@api_view(['GET'])
def classroom_based_rawdata(request):
    classroom = request.GET.get('classroom')
    if not classroom:
        return Response({"error": "classroom required"}, status=400)

    # Get In-class Weather data
    weather = ProjectInclassWeather.objects.filter(classroom=classroom)
    if not weather.exists():
        return Response({"error": "no data can't find Date Range"}, status=404)

    start_time = weather.order_by('timestamp').first().timestamp
    end_time = weather.order_by('-timestamp').first().timestamp
    start_time_adj = start_time - timedelta(minutes=40)  # Time Buffer
    end_time_adj = end_time + timedelta(minutes=40)      # Time Buffer

    # Get In-class Attendance data
    attendance = ProjectInclassAttendance.objects.using('people_db').filter(classroom=classroom).values()

    # Get TMD data
    tmd = Tmd_weather.objects.using('people_db').filter(create_time__range=[start_time_adj, end_time_adj]).values()

    return Response([{
        "weather": list(weather.values()),
        "attendance": list(attendance.values()),
        "tmd": list(tmd.values()),
        "start_time": start_time,
        "end_time": end_time
    }])


@extend_schema(
    parameters=[
        OpenApiParameter(name='start',description='Start datetime (YYYY-MM-DD HH:MM:SS)',required=True,type=str),
        OpenApiParameter(name='end',description='End datetime (YYYY-MM-DD HH:MM:SS)',required=True,type=str),
        OpenApiParameter(name='limit',description='Number of records',required=False,type=int),
    ]
)
@api_view(['GET'])
def daterange_based_rawdata(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    limit = request.GET.get('limit')

    try:
        # Primary data
        weather = ProjectInclassWeather.objects.filter(
            timestamp__range=[start, end]
        ).values()
        attendance = ProjectInclassAttendance.objects.using('people_db').filter(
            timestamp__range=[start, end]
        ).values()

        # Secondary data
        tmd = Tmd_weather.objects.using('people_db').filter(
            create_time__range=[start, end]
        ).values()

        if limit:
            weather = weather[:int(limit)]
            attendance = attendance[:int(limit)]
            tmd = attendance[:int(limit)]
    except ValueError:
        return Response({"error": "Limit must be numbers. start time is required, and your daily format might be incorrect."}, status=400)

    return Response([{
        "weather": list(weather),
        "attendance": list(attendance),
        "tmd": list(tmd)
    }])


@extend_schema(
    parameters=[
        OpenApiParameter(name='classroom', description='Name of the course', required=True, type=str),
    ]
)
@api_view(['GET'])
def classroom_based_aggregated(request):
    classroom = request.GET.get('classroom')
    if not classroom:
        return Response({"error": "classroom required"}, status=400)

    # Get In-class Weather data
    weather = ProjectInclassWeather.objects.filter(classroom=classroom)
    if not weather.exists():
        return Response({"error": "no data"}, status=404)

    start_time = weather.order_by('timestamp').first().timestamp
    end_time = weather.order_by('-timestamp').first().timestamp
    start_time_adj = start_time - timedelta(minutes=40)
    end_time_adj = end_time + timedelta(minutes=40)

    # Get In-class Attendance data
    attendance = ProjectInclassAttendance.objects.using('people_db').filter(classroom=classroom)

    # Get TMD data
    tmd = Tmd_weather.objects.using('people_db').filter(create_time__range=[start_time_adj, end_time_adj])

    # Aggregations
    weather_stats = weather.aggregate(
        avg_temp=Avg('temp_c'),
        max_temp=Max('temp_c'),
        min_temp=Min('temp_c'),

        avg_humid=Avg('humid_p'),
        max_humid=Max('humid_p'),
        min_humid=Min('humid_p'),

        avg_light=Avg('light_l'),
        max_light=Max('light_l'),
        min_light=Min('light_l'),

        avg_sound=Avg('sound_adc'),
        max_sound=Max('sound_adc'),
        min_sound=Min('sound_adc'),
    )

    attendance_stats = attendance.aggregate(
        total_in=Count('id', filter=Q(direction='IN')),
        total_out=Count('id', filter=Q(direction='OUT')),
    )

    tmd_stats = tmd.aggregate(
        tmd_avg_temp=Avg('temp_c'),
        tmd_max_temp=Max('temp_c'),
        tmd_min_temp=Min('temp_c'),

        tmd_avg_humid=Avg('humid_p'),
        tmd_max_humid=Max('humid_p'),
        tmd_min_humid=Min('humid_p'),

        avg_rainfall_mm=Avg('rainfall_mm'),
        max_rainfall_mm=Max('rainfall_mm'),
        min_rainfall_mm=Min('rainfall_mm'),

        lat =Avg('lat'),
        lon =Avg('lon'),
    )

    return Response({
        "weather": weather_stats,
        "attendance": attendance_stats,
        "tmd": tmd_stats,
        "start_time": start_time,
        "end_time": end_time
    })