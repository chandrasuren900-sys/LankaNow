import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.text import slugify
from news.models import Article,Category,AuditLog
class Command(BaseCommand):
    help='Import exported prototype JSON as drafts for editorial review. Existing slugs are skipped.'
    def add_arguments(self,p): p.add_argument('file');p.add_argument('--author',required=True)
    def handle(self,*args,**o):
        try: author=User.objects.get(username=o['author'],is_staff=True)
        except User.DoesNotExist: raise CommandError('Choose an existing staff username.')
        try: data=json.loads(Path(o['file']).read_text(encoding='utf-8'))
        except (ValueError,OSError) as e: raise CommandError(str(e))
        if not isinstance(data,list): raise CommandError('Expected a JSON array of articles.')
        count=0
        with transaction.atomic():
            for i,row in enumerate(data):
                if not isinstance(row,dict) or not str(row.get('title','')).strip(): raise CommandError(f'Row {i+1} has no title.')
                slug=slugify(str(row.get('slug') or row['title']),allow_unicode=True)[:230] or f'imported-{i+1}'
                if Article.objects.filter(slug=slug).exists(): continue
                category=Category.objects.filter(slug=slugify(str(row.get('category','news')))).first() or Category.objects.get(slug='news')
                a=Article(title=str(row['title'])[:220],slug=slug,author=author,category=category,summary=str(row.get('summary') or row.get('excerpt') or 'Summary needed — please review.')[:600],content=str(row.get('content') or row.get('body') or 'Article body needed — please review.'),status='draft')
                a.full_clean();a.save();count+=1
                AuditLog.objects.create(actor=author,action=f'Imported prototype draft #{a.pk}: {a.title}')
        self.stdout.write(f'Imported {count} drafts. Check body formatting and upload images before publication. No prototype publication flags or credentials were trusted.')
