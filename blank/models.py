from django.db import models
class Employee(models.Model):
 eno=models.CharField(max_length=24,primary_key=True)
 display_name=models.CharField(max_length=120)
 enabled=models.BooleanField(default=True)
 is_admin=models.BooleanField(default=False)
class Vehicle(models.Model):
 id=models.CharField(max_length=100,primary_key=True)
 employee=models.ForeignKey(Employee,on_delete=models.PROTECT)
 details=models.JSONField(default=dict)
 photo=models.BinaryField()
 photo_type=models.CharField(max_length=60,default="image/jpeg")
