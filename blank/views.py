import json,re,os
from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
from .models import Employee,Vehicle

def index(request):return render(request,"index.html")
def fail(msg,code):return JsonResponse({"detail":msg},status=code)
def account(req):
 eno=req.session.get("eno")
 return Employee.objects.filter(eno=eno,enabled=True).first() if eno else None
@csrf_exempt
def api(request,endpoint,record_id=None):
 if endpoint=="login" and request.method=="POST":
  try:p=json.loads(request.body)
  except ValueError:return fail("Invalid JSON",400)
  u=Employee.objects.filter(eno__iexact=str(p.get("eno","")).strip(),enabled=True).first()
  if not u or (u.is_admin and not check_password(str(p.get("password","")),os.environ.get("CAK_ADMIN_PASSWORD_HASH","!"))):return fail("Invalid E-number or administrator password",401)
  request.session.cycle_key();request.session["eno"]=u.eno;request.session.set_expiry(14*86400)
  return JsonResponse({"eno":u.eno,"name":u.display_name,"admin":u.is_admin})
 if endpoint=="logout" and request.method=="POST":request.session.flush();return JsonResponse({"ok":True})
 u=account(request)
 if not u:return fail("Login required",401)
 if endpoint=="me" and request.method=="GET":return JsonResponse({"eno":u.eno,"name":u.display_name,"admin":u.is_admin})
 if endpoint=="employees":
  if not u.is_admin:return fail("Administrator only",403)
  if request.method=="GET":return JsonResponse([{"eno":e.eno,"name":e.display_name,"enabled":e.enabled,"admin":e.is_admin} for e in Employee.objects.order_by("eno")],safe=False)
  if request.method=="POST":
   try:d=json.loads(request.body)
   except ValueError:return fail("Invalid JSON",400)
   eno=str(d.get("eno","")).strip().upper();name=str(d.get("name","")).strip()
   if not re.fullmatch(r"E[A-Z0-9]{2,20}",eno) or eno=="EADMIN" or not name:return fail("Invalid employee number or name",400)
   if Employee.objects.filter(eno=eno).exists():return fail("Employee exists",409)
   Employee.objects.create(eno=eno,display_name=name);return JsonResponse({"ok":True})
 if endpoint=="records":
  if record_id and request.method=="DELETE":
   v=Vehicle.objects.filter(id=record_id).first()
   if not v:return fail("Not found",404)
   if v.employee_id!=u.eno and not u.is_admin:return fail("Not your record",403)
   v.delete();return JsonResponse({"ok":True})
  if request.method=="GET":
   qs=Vehicle.objects.all() if u.is_admin else Vehicle.objects.filter(employee=u)
   return JsonResponse([dict(v.details,id=v.id,employee=v.employee_id) for v in qs.order_by("-id")],safe=False)
  if request.method=="POST":
   try:d=json.loads(request.POST["details"])
   except (ValueError,KeyError):return fail("Invalid record",400)
   rid=str(d.get("id",""))
   if not re.fullmatch(r"[A-Za-z0-9_-]{5,100}",rid) or d.get("folder") not in ("Clean Parking","Down to Washbay"):return fail("Invalid record",400)
   photo=request.FILES.get("photo")
   if not photo or photo.size>12*1024*1024:return fail("Photo missing or over 12MB",413)
   if photo.content_type not in ("image/jpeg","image/png","image/webp","image/heic","image/heif"):return fail("Unsupported photo",415)
   existing=Vehicle.objects.filter(id=rid).first()
   if existing and existing.employee_id!=u.eno and not u.is_admin:return fail("Not your record",403)
   d.pop("blob",None);d.pop("employee",None)
   Vehicle.objects.update_or_create(id=rid,defaults={"employee":existing.employee if existing else u,"details":d,"photo":photo.read(),"photo_type":photo.content_type})
   return JsonResponse({"ok":True})
 if endpoint=="photos" and record_id and request.method=="GET":
  v=Vehicle.objects.filter(id=record_id).first()
  if not v or (v.employee_id!=u.eno and not u.is_admin):return fail("Photo not found",404)
  r=HttpResponse(bytes(v.photo),content_type=v.photo_type);r["Cache-Control"]="private, no-store";return r
 return fail("Not found",404)
