from django.db import migrations,models
import django.db.models.deletion
def admin(apps,schema_editor):
 apps.get_model("blank","Employee").objects.get_or_create(eno="EAdmin",defaults={"display_name":"Administrator","is_admin":True,"enabled":True})
class Migration(migrations.Migration):
 initial=True
 dependencies=[]
 operations=[migrations.CreateModel(name="Employee",fields=[("eno",models.CharField(max_length=24,primary_key=True,serialize=False)),("display_name",models.CharField(max_length=120)),("enabled",models.BooleanField(default=True)),("is_admin",models.BooleanField(default=False))]),migrations.CreateModel(name="Vehicle",fields=[("id",models.CharField(max_length=100,primary_key=True,serialize=False)),("details",models.JSONField(default=dict)),("photo",models.BinaryField()),("photo_type",models.CharField(default="image/jpeg",max_length=60)),("employee",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,to="blank.employee"))]),migrations.RunPython(admin,migrations.RunPython.noop)]
