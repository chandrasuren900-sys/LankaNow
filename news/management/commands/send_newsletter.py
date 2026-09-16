from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from django.core.mail import send_mail
from django.conf import settings
from django.core import signing
from news.models import Subscriber
class Command(BaseCommand):
    help='Send a plain-text newsletter to confirmed subscribers. Requires explicit --send.'
    def add_arguments(self,p):
        p.add_argument('--subject',required=True);p.add_argument('--body-file',required=True);p.add_argument('--send',action='store_true')
    def handle(self,*args,**o):
        body=Path(o['body_file']).read_text(encoding='utf-8')
        subscribers=Subscriber.objects.filter(confirmed=True)
        self.stdout.write(f'Confirmed recipients: {subscribers.count()}')
        if not o['send']: self.stdout.write('Dry run. Add --send to deliver.');return
        if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL: raise CommandError('Configure SMTP first.')
        for s in subscribers:
            token=signing.dumps(s.email,salt='unsubscribe')
            send_mail(o['subject'],body+'\n\nUnsubscribe: '+settings.SITE_URL+'/newsletter/unsubscribe/'+token+'/',settings.DEFAULT_FROM_EMAIL,[s.email])
        self.stdout.write('Delivery completed.')
