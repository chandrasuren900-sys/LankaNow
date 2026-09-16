from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from news.models import Category,SiteSettings
CATEGORIES=[('News','The headlines and developments shaping Sri Lanka.'),('Trending','The stories drawing readers’ attention, ranked by views and recency.'),('People','The voices, ideas and lives behind the headlines.'),('Viral','The conversations travelling across the internet.'),('Sports','From the pitch to the podium. Follow the action.'),('Entertainment','Film, music, culture and the people making it happen.'),('Jobs','Opportunities for your next chapter.'),('Deals','Useful finds and offers for everyday life.'),('Events','Discover what’s happening around the island.'),('Food','The flavours, kitchens and communities of Sri Lanka.'),('Travel','Familiar places, fresh perspectives and new destinations.'),('Tech','Ideas and technology changing the way we live.')]
class Command(BaseCommand):
    help='Create categories, role permissions and publication settings; no sample stories or credentials.'
    def handle(self,*args,**options):
        for i,(name,description) in enumerate(CATEGORIES): Category.objects.get_or_create(slug=name.lower(),defaults={'name':name,'description':description,'order':i})
        SiteSettings.objects.get_or_create(pk=1)
        base=['view_article','add_article','change_article','view_category','view_tag','add_tag','view_media','add_media','change_media']
        for role in ['Reporter','Author','Editor','Admin']:
            group,created=Group.objects.get_or_create(name=role)
            perms=Permission.objects.filter(content_type__app_label='news')
            if role=='Admin': perms=perms.exclude(content_type__model__in=['ratebucket','auditlog']).exclude(codename__in=['add_articleview','change_articleview','delete_articleview'])
            else: perms=perms.filter(codename__in=base)
            if created: group.permissions.set(perms)
        self.stdout.write(self.style.SUCCESS('Newsroom configured. Create a superuser with: python manage.py createsuperuser'))
