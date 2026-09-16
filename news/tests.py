from io import BytesIO
from datetime import timedelta
from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User,Group
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from PIL import Image
from .models import *
import tempfile

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class NewsroomTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('setup_newsroom',verbosity=0)
        cls.root=User.objects.create_superuser('publisher','publisher@example.test','a-long-test-password!7')
        cls.author=User.objects.create_user('writer',password='a-long-test-password!8',is_staff=True)
        cls.author.groups.add(Group.objects.get(name='Author'))
        cls.other=User.objects.create_user('other',password='a-long-test-password!9',is_staff=True)
        cls.other.groups.add(Group.objects.get(name='Author'))
        cls.category=Category.objects.get(slug='news')
        cls.draft=Article.objects.create(title='Private draft',slug='private-draft',summary='A private summary',content='Private body',category=cls.category,author=cls.author)
        cls.live=Article.objects.create(title='Public story',slug='public-story',summary='A public summary',content='Body paragraph.\n\nSecond paragraph.',category=cls.category,author=cls.root,status='published')
    def test_public_routes_and_no_admin_controls(self):
        for url in ['/','/news/','/trending/','/people/','/viral/','/sports/','/entertainment/','/jobs/','/deals/','/events/','/food/','/travel/','/tech/','/about/','/privacy/','/terms/','/contact/','/search/?q=Public']:
            with self.subTest(url=url):
                response=self.client.get(url)
                self.assertEqual(response.status_code,200)
                self.assertNotContains(response,'href="/admin/')
                self.assertNotContains(response,'Private draft')
    def test_drafts_hidden_everywhere(self):
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code,404)
        self.assertNotContains(self.client.get('/api/articles/'),'Private draft')
        self.assertNotContains(self.client.get('/sitemap.xml'),'private-draft')
        self.assertNotContains(self.client.get('/search/?q=Private'),'Private draft')
    def test_no_anonymous_admin_access(self):
        for url in ['/admin/','/admin/news/article/add/','/admin/news/article/','/admin/analytics/','/admin/preview/1/']:
            self.assertEqual(self.client.get(url).status_code,302)
    def test_legacy_editor_redirect_is_protected(self):
        response=self.client.get('/admin/editor.html',follow=True)
        self.assertContains(response,'Sign in with your staff account')
        self.assertNotContains(response,'name="content"')
    def test_non_staff_has_no_admin_access(self):
        visitor=User.objects.create_user('visitor',password='long-enough-password!')
        self.client.force_login(visitor)
        self.assertEqual(self.client.get('/admin/').status_code,302)
    def test_author_cannot_edit_another_authors_story(self):
        self.client.force_login(self.other)
        response=self.client.get(reverse('newsroom:news_article_change',args=[self.draft.pk]))
        self.assertIn(response.status_code,[302,403,404])
        self.assertNotContains(self.client.get('/admin/news/article/'),'Private draft')
        self.assertEqual(self.client.get(reverse('newsroom:preview',args=[self.draft.pk])).status_code,403)
    def payload(self,**kw):
        return {'title':'New story','slug':'new-story','category':self.category.pk,'summary':'A summary','content':'Actual body','status':'draft',**kw}
    def test_author_can_save_draft_with_server_assigned_author(self):
        self.client.force_login(self.author)
        response=self.client.post('/admin/news/article/add/',self.payload(author=self.root.pk))
        self.assertEqual(response.status_code,302)
        self.assertEqual(Article.objects.get(slug='new-story').author,self.author)
    def test_author_cannot_publish_forged_post(self):
        self.client.force_login(self.author)
        response=self.client.post('/admin/news/article/add/',self.payload(status='published'))
        self.assertEqual(response.status_code,200)
        self.assertFalse(Article.objects.filter(slug='new-story').exists())
    def test_author_cannot_modify_published_story(self):
        self.live.author=self.author;self.live.save()
        self.client.force_login(self.author)
        response=self.client.post(reverse('newsroom:news_article_change',args=[self.live.pk]),self.payload())
        self.assertEqual(response.status_code,403)
    def test_publisher_can_publish(self):
        self.client.force_login(self.root)
        response=self.client.post('/admin/news/article/add/',self.payload(status='published',author=self.root.pk))
        self.assertEqual(response.status_code,302)
        story=Article.objects.get(slug='new-story')
        self.assertIsNotNone(story.published_at)
        self.assertEqual(self.client.get(story.get_absolute_url()).status_code,200)
        self.assertTrue(AuditLog.objects.filter(action__contains='new-story').exists() or AuditLog.objects.filter(action__contains='New story').exists())
    def test_scheduler_publishes_only_due_stories(self):
        future=Article.objects.create(title='Future',slug='future',summary='Summary',content='Body',author=self.root,category=self.category,status='scheduled',published_at=timezone.now()+timedelta(days=1))
        due=Article.objects.create(title='Due',slug='due',summary='Summary',content='Body',author=self.root,category=self.category,status='scheduled',published_at=timezone.now()-timedelta(minutes=1))
        call_command('publish_due')
        future.refresh_from_db();due.refresh_from_db()
        self.assertEqual(future.status,'scheduled');self.assertEqual(due.status,'published')
    def test_xss_is_escaped(self):
        self.live.content='<script>alert(1)</script>';self.live.title='</script><script>alert(2)</script>';self.live.save()
        response=self.client.get(self.live.get_absolute_url())
        self.assertNotContains(response,'<script>alert(')
        self.assertContains(response,'&lt;script&gt;alert(1)&lt;/script&gt;')
    def test_real_article_view_counts(self):
        before=self.live.views
        self.client.get(self.live.get_absolute_url())
        self.live.refresh_from_db();self.assertEqual(self.live.views,before+1)
        self.assertEqual(ArticleView.objects.get(article=self.live).count,1)
    def test_csrf_blocks_writes(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.root)
        self.assertEqual(client.post('/admin/news/article/add/',self.payload()).status_code,403)
        self.assertEqual(client.post('/contact/',{'name':'x','email':'x@example.test','message':'hi'}).status_code,403)
    def test_api_is_read_only(self): self.assertEqual(self.client.post('/api/articles/',{}).status_code,405)
    def test_login_rate_limit(self):
        for _ in range(20): self.client.post('/admin/login/',{'username':'bad','password':'bad'})
        self.assertEqual(self.client.post('/admin/login/',{}).status_code,429)
    def test_search_tags_authors_and_injection(self):
        tag=Tag.objects.create(name='Culture');self.live.tags.add(tag)
        self.assertContains(self.client.get('/search/?q=Culture'),'Public story')
        self.assertContains(self.client.get('/search/?q=publisher'),'Public story')
        self.assertEqual(self.client.get('/search/',{'q':"' OR 1=1 --"}).status_code,200)
    def test_contact_is_saved(self):
        response=self.client.post('/contact/',{'name':'Reader','email':'reader@example.test','message':'A correction request.'})
        self.assertEqual(response.status_code,302);self.assertEqual(ContactMessage.objects.count(),1)
    @override_settings(EMAIL_HOST='',DEFAULT_FROM_EMAIL='')
    def test_newsletter_does_not_fake_signup(self):
        response=self.client.post('/newsletter/subscribe/',{'email':'reader@example.test','consent':'on'},follow=True)
        self.assertContains(response,'Newsletter signup is not available yet.')
        self.assertEqual(Subscriber.objects.count(),0)
    def test_admin_pages_render(self):
        self.client.force_login(self.root)
        for url in ['/admin/','/admin/news/article/add/','/admin/news/media/add/','/admin/news/category/','/admin/auth/user/','/admin/analytics/','/admin/news/sitesettings/','/admin/news/auditlog/']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_upload_rejects_disguised_executable(self):
        media=Media(title='Bad',alt_text='Bad',uploaded_by=self.root,image=SimpleUploadedFile('photo.jpg',b'<script>not an image</script>',content_type='image/jpeg'))
        with self.assertRaises(ValidationError): media.clean()
    def test_upload_reencodes_and_private_media_not_public(self):
        data=BytesIO();Image.new('RGB',(120,120),'red').save(data,'PNG')
        with tempfile.TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            media=Media.objects.create(title='Test',alt_text='Red square',uploaded_by=self.root,image=SimpleUploadedFile('a.png',data.getvalue(),content_type='image/png'))
            self.assertTrue(media.image.name.endswith('.webp'))
            self.assertEqual(self.client.get(media.image.url).status_code,404)
            self.live.featured_image=media;self.live.save()
            self.assertEqual(self.client.get(media.image.url).status_code,200)
    def test_logout_invalidates_session(self):
        self.client.force_login(self.root);self.client.post('/admin/logout/')
        self.assertEqual(self.client.get('/admin/').status_code,302)
    def test_password_reset_pages(self):
        self.assertEqual(self.client.get('/accounts/password-reset/').status_code,200)
    @override_settings(EMAIL_HOST='smtp.example.test',DEFAULT_FROM_EMAIL='news@example.test',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_newsletter_confirmation_and_unsubscribe(self):
        from django.core import mail,signing
        response=self.client.post('/newsletter/subscribe/',{'email':'reader@example.test','consent':'on'})
        self.assertEqual(response.status_code,302);self.assertEqual(len(mail.outbox),1)
        self.assertFalse(Subscriber.objects.get().confirmed)
        token=signing.dumps('reader@example.test',salt='newsletter')
        self.client.get('/newsletter/confirm/'+token+'/')
        self.assertFalse(Subscriber.objects.get().confirmed)
        self.client.post('/newsletter/confirm/'+token+'/')
        self.assertTrue(Subscriber.objects.get().confirmed)
        unsubscribe=signing.dumps('reader@example.test',salt='unsubscribe')
        self.client.post('/newsletter/unsubscribe/'+unsubscribe+'/')
        self.assertFalse(Subscriber.objects.exists())
    @override_settings(EMAIL_HOST='smtp.example.test',DEFAULT_FROM_EMAIL='news@example.test',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_delivers_only_generic_result(self):
        from django.core import mail
        response=self.client.post('/accounts/password-reset/',{'email':'publisher@example.test'},follow=True)
        self.assertEqual(response.status_code,200);self.assertEqual(len(mail.outbox),1)
        self.assertContains(response,'If an active account matches')
    def test_unicode_article_url(self):
        self.live.slug='தமிழ்';self.live.save()
        self.assertEqual(self.client.get(self.live.get_absolute_url()).status_code,200)
    def test_setup_preserves_customized_group_permissions(self):
        group=Group.objects.get(name='Editor');group.permissions.clear()
        call_command('setup_newsroom',verbosity=0)
        self.assertEqual(group.permissions.count(),0)
