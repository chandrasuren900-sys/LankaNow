import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django.urls import reverse

class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=240, blank=True)
    order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['order','name']
        verbose_name_plural = 'Categories'
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('category',args=[self.slug])

class Tag(models.Model):
    name = models.CharField(max_length=60,unique=True)
    def __str__(self): return self.name

def media_path(instance, filename): return 'images/'+uuid.uuid4().hex+'.webp'

class Media(models.Model):
    title = models.CharField(max_length=150)
    image = models.ImageField(upload_to=media_path)
    alt_text = models.CharField(max_length=240)
    caption = models.CharField(max_length=400,blank=True)
    credit = models.CharField(max_length=160,blank=True)
    uploaded_by = models.ForeignKey(User,on_delete=models.PROTECT,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.image and not self.image._committed:
            if self.image.size > 5*1024*1024: raise ValidationError({'image':'Maximum upload size is 5 MB.'})
            try:
                self.image.seek(0)
                with Image.open(self.image) as im:
                    if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>24000000:
                        raise ValidationError({'image':'Use JPEG, PNG or WebP up to 24 megapixels.'})
                    im.verify()
                self.image.seek(0)
            except (UnidentifiedImageError,OSError,Image.DecompressionBombError):
                raise ValidationError({'image':'The image could not be verified.'})
    def save(self,*args,**kwargs):
        self.clean()
        if self.image and not self.image._committed:
            from PIL import ImageOps
            self.image.seek(0)
            with Image.open(self.image) as source:
                im=ImageOps.exif_transpose(source).convert('RGB')
                im.thumbnail((2000,2000))
                data=BytesIO(); im.save(data,'WEBP',quality=85)
            self.image.save('image.webp',ContentFile(data.getvalue()),save=False)
        super().save(*args,**kwargs)
    class Meta:
        verbose_name_plural='Media library'
    def __str__(self): return self.title

class ArticleQuerySet(models.QuerySet):
    def published(self): return self.filter(status='published',published_at__lte=timezone.now())

class Article(models.Model):
    STATUS = [('draft','Draft'),('review','In review'),('scheduled','Scheduled'),('published','Published'),('archived','Archived')]
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240,unique=True,allow_unicode=True)
    category = models.ForeignKey(Category,on_delete=models.PROTECT)
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    summary = models.TextField(max_length=600)
    content = models.TextField(help_text='Plain text; separate paragraphs with a blank line. HTML is escaped for safety.')
    featured_image = models.ForeignKey(Media,null=True,blank=True,on_delete=models.PROTECT)
    tags = models.ManyToManyField(Tag,blank=True)
    status = models.CharField(max_length=12,choices=STATUS,default='draft',db_index=True)
    featured = models.BooleanField(default=False)
    breaking = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=70,blank=True)
    seo_description = models.CharField(max_length=170,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True,blank=True,db_index=True)
    views = models.PositiveIntegerField(default=0,editable=False)
    objects = ArticleQuerySet.as_manager()
    class Meta:
        ordering = ['-published_at','-created_at']
        permissions = [('publish_article','Can publish and schedule articles')]
        indexes = [models.Index(fields=['status','category','published_at'])]
    def clean(self):
        if self.status=='scheduled' and (not self.published_at or self.published_at<=timezone.now()):
            raise ValidationError({'published_at':'Scheduling requires a future publication time.'})
        if self.status=='published' and self.published_at and self.published_at>timezone.now():
            raise ValidationError({'published_at':'Choose Scheduled for a future publication time.'})
    def save(self,*args,**kwargs):
        if self.status=='published' and not self.published_at: self.published_at=timezone.now()
        super().save(*args,**kwargs)
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('article',args=[self.slug])
    @property
    def reading_minutes(self): return max(1,round(len(self.content.split())/200))

class ArticleView(models.Model):
    article = models.ForeignKey(Article,on_delete=models.CASCADE)
    day = models.DateField(default=timezone.localdate)
    count = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['article','day'],name='article_day')]

class AuditLog(models.Model):
    actor = models.ForeignKey(User,null=True,on_delete=models.SET_NULL)
    action = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
    def __str__(self): return self.action

class RateBucket(models.Model):
    key = models.CharField(max_length=64,unique=True)
    count = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField()

class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.email

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    def __str__(self): return f'{self.name} — {self.created_at:%d %b %Y}'

class SiteSettings(models.Model):
    name = models.CharField(max_length=80,default='LankaNow')
    tagline = models.CharField(max_length=100,default='Know Now.')
    contact_email = models.EmailField(blank=True)
    about = models.TextField(default='LankaNow brings news, people and everyday discoveries from across Sri Lanka into one place.')
    privacy = models.TextField(default='We store messages submitted through our contact form and newsletter registrations. Essential session cookies support authentication and form security. Article views are counted without advertising identifiers. Contact us to request access to or deletion of submitted personal data.')
    terms = models.TextField(default='LankaNow content is provided for general information. Please contact our newsroom to report corrections or discuss permissions to reuse original material.')
    def __str__(self): return 'Publication settings'
