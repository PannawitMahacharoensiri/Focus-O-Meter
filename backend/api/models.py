from django.db import models

# Primary data : 
class ProjectInclassWeather(models.Model):
    temp_c = models.FloatField()
    light_l = models.FloatField()
    humid_p = models.FloatField()
    sound_adc = models.FloatField(db_column='sound_ADC')  # Field name made lowercase.
    measuretime = models.DateTimeField(db_column='measureTime')  # Field name made lowercase.
    timestamp = models.DateTimeField(db_column='timeStamp')  # Field name made lowercase.
    classroom = models.CharField(db_column='class', max_length=50, blank=True, null=True)  # Field renamed because it was a Python reserved word.
    objects = models.Manager() 

    class Meta:
        managed = False
        db_table = 'inclass_weather'
    


class ProjectInclassAttendance(models.Model):
    classroom = models.CharField(max_length=50, blank=True, null=True)
    direction = models.CharField(max_length=3, blank=True, null=True)
    timestamp = models.DateTimeField(blank=True, null=True)
    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'project_inclass_attendance'


# Secondary data : 
class Tmd_weather(models.Model):
    temp_c = models.FloatField()
    humid_p = models.FloatField()
    rainfall_mm = models.FloatField(db_column='rainfal_mm')
    lat = models.FloatField()
    lon = models.FloatField()
    create_time = models.DateTimeField(unique=True)
    objects = models.Manager()

    class Meta:
        managed = False
        db_table = 'tmd'
        