from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ProjectInclassWeather, ProjectInclassAttendance, Tmd_weather
from drf_spectacular.utils import extend_schema, OpenApiParameter


@extend_schema(
    parameters=[
        OpenApiParameter(name='limit', description='Number of records', required=False, type=int),
        OpenApiParameter(name='offset', description='Start position', required=False, type=int),
    ]
)
@api_view(['GET'])
def weather_data(request):
    limit = request.GET.get('limit')
    offset = request.GET.get('offset')

    data = ProjectInclassWeather.objects.all().values()

    try:
        if offset:
            data = data[int(offset):]
        if limit:
            data = data[:int(limit)]
    except:
        return Response({"error": "limit/offset must be numbers"}, status=400)

    return Response(list(data))


@extend_schema(
    parameters=[
        OpenApiParameter(name='limit', description='Number of records', required=False, type=int),
        OpenApiParameter(name='offset', description='Start position', required=False, type=int),
    ]
)
@api_view(['GET'])
def attendance_data(request):
    limit = request.GET.get('limit')
    offset = request.GET.get('offset')

    data = ProjectInclassAttendance.objects.using('people_db').all().values()

    try:
        if offset:
            data = data[int(offset):]
        if limit:
            data = data[:int(limit)]
    except:
        return Response({"error": "limit/offset must be numbers"}, status=400)

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
    except:
        return Response({"error": "limit/offset must be numbers"}, status=400)

    return Response(list(data))