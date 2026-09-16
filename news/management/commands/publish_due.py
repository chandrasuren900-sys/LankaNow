from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from news.models import Article,AuditLog,RateBucket
class Command(BaseCommand):
    help='Publish due scheduled stories. Run every minute with cron or a scheduler.'
    def handle(self,*args,**options):
        count=0
        with transaction.atomic():
            for article in Article.objects.select_for_update().filter(status='scheduled',published_at__lte=timezone.now()):
                article.status='published'; article.save(update_fields=['status','updated_at'])
                AuditLog.objects.create(action=f'Scheduled publication: #{article.pk} {article.title}')
                count+=1
            RateBucket.objects.filter(expires__lt=timezone.now()).delete()
        self.stdout.write(f'Published {count} scheduled stories.')
