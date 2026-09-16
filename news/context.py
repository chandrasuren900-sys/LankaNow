from .models import Category, SiteSettings
from django.conf import settings
def brand(request):
    return {'categories':Category.objects.all(),'publication':SiteSettings.objects.first(),'site_url':settings.SITE_URL,'canonical':settings.SITE_URL+request.path,'mail_available':bool(settings.EMAIL_HOST and settings.DEFAULT_FROM_EMAIL)}
