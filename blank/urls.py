from django.urls import path
from . import views
urlpatterns=[path("",views.index,name="index"),path("api/<str:endpoint>",views.api),path("api/<str:endpoint>/<str:record_id>",views.api)]
