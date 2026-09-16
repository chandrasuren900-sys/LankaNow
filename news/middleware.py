import hashlib
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponse
from django.conf import settings
from .models import RateBucket

def limited(request,scope,limit=10):
    # REMOTE_ADDR must be restored by a trusted reverse proxy; never trust arbitrary forwarding headers.
    identity=request.META.get('REMOTE_ADDR','unknown')
    key=hashlib.sha256((settings.SECRET_KEY+scope+identity).encode()).hexdigest()
    now=timezone.now()
    with transaction.atomic():
        row,_=RateBucket.objects.select_for_update().get_or_create(key=key,defaults={'expires':now+timedelta(minutes=15)})
        if row.expires<=now: row.count=0; row.expires=now+timedelta(minutes=15)
        row.count+=1; row.save()
        return row.count>limit

class GuardMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.method=='POST' and (request.path.startswith('/admin/login') or request.path.startswith('/accounts/')):
            if limited(request,'auth',20):
                return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429,headers={'Retry-After':'900'})
        response=self.get_response(request)
        if request.path.startswith(('/admin/','/accounts/')):
            response['Cache-Control']='no-store'
            response['X-Robots-Tag']='noindex, nofollow'
        else:
            response['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        return response
