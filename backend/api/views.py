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
    parameters=[
        OpenApiParameter(name='start',description='Start datetime (YYYY-MM-DD HH:MM:SS)',required=True,type=str),
        OpenApiParameter(name='end',description='End datetime (YYYY-MM-DD HH:MM:SS)',required=True,type=str),
        OpenApiParameter(name='limit',description='Number of records',required=False,type=int),
    ]
)
@api_view(['GET'])
def data_in_daterange(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    limit = request.GET.get('limit')

    try:
        # Primary data
        weather = ProjectInclassWeather.objects.filter(
            measuretime__range=[start, end]
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

    return Response({
        "weather": list(weather),
        "attendance": list(attendance),
        "tmd": list(tmd)
    })