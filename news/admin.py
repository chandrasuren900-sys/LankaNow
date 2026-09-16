from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django import forms
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, render
from django.utils.html import format_html
from .models import *

class NewsroomSite(admin.AdminSite):
    site_header='LankaNow / Newsroom'
    site_title='LankaNow Newsroom'
    index_title='Your newsroom, at a glance'
    index_template='admin/newsroom_index.html'
    def get_urls(self):
        return [path('preview/<int:pk>/',self.admin_view(self.preview),name='preview'),path('analytics/',self.admin_view(self.analytics),name='analytics')]+super().get_urls()
    def preview(self,request,pk):
        article=get_object_or_404(Article.objects.select_related('author','category','featured_image'),pk=pk)
        if not request.user.has_perm('news.view_article') or (not request.user.has_perm('news.publish_article') and article.author_id!=request.user.id): raise PermissionDenied
        return render(request,'news/article.html',{'article':article,'preview':True})
    def analytics(self,request):
        if not request.user.has_perm('news.view_articleview'): raise PermissionDenied
        return render(request,'admin/analytics.html',{**self.each_context(request),'title':'Audience overview','top':Article.objects.order_by('-views')[:10],'daily':ArticleView.objects.values('day').annotate(total=Sum('count')).order_by('-day')[:30],'by_category':Article.objects.values('category__name').annotate(total=Sum('views')).order_by('-total'),'total_views':Article.objects.aggregate(n=Sum('views'))['n'] or 0})
    def index(self,request,extra_context=None):
        articles=Article.objects.all()
        if not request.user.has_perm('news.publish_article'): articles=articles.filter(author=request.user)
        data={'metrics':[('Total articles',articles.count())]+[(label,articles.filter(status=status).count()) for status,label in Article.STATUS]+[('Article views',articles.aggregate(n=Sum('views'))['n'] or 0),('Categories',Category.objects.count()),('Staff',User.objects.filter(is_staff=True,is_active=True).count())],'recent_articles':articles.select_related('author','category')[:6],'activity':AuditLog.objects.all()[:6] if request.user.is_superuser else AuditLog.objects.filter(actor=request.user)[:6]}
        return super().index(request,{**data,**(extra_context or {})})
site=NewsroomSite(name='newsroom')

class ArticleForm(forms.ModelForm):
    class Meta:
        model=Article
        fields='__all__'
    def __init__(self,*args,user=None,**kwargs):
        self.user=user
        super().__init__(*args,**kwargs)
        if user and not user.has_perm('news.publish_article'):
            self.fields['status'].choices=[('draft','Draft'),('review','In review')]
    def clean(self):
        data=super().clean()
        if self.user and not self.user.has_perm('news.publish_article'):
            if data.get('status') not in ('draft','review'): raise forms.ValidationError('Only a publisher can publish or schedule articles.')
            if self.instance.pk and Article.objects.get(pk=self.instance.pk).status in ('published','scheduled','archived'):
                raise forms.ValidationError('Ask a publisher to return this story to draft before editing.')
        return data

@admin.register(Article,site=site)
class ArticleAdmin(admin.ModelAdmin):
    form=ArticleForm
    list_display=('title','category','author','status','breaking','published_at','views','preview_link')
    list_filter=('status','category','author','breaking','featured','published_at')
    search_fields=('title','summary','content','tags__name','author__username')
    date_hierarchy='created_at'
    list_per_page=20
    autocomplete_fields=('featured_image','tags')
    prepopulated_fields={'slug':('title',)}
    readonly_fields=('created_at','updated_at','views','preview_link')
    fieldsets=(('The story',{'fields':('title','slug','category','author','summary','content')}),('Visuals & discovery',{'fields':('featured_image','tags','featured','breaking')}),('Publishing',{'fields':('status','published_at','preview_link'),'description':'Save to preview. Times use Asia/Colombo. Scheduled stories require the publish_due command running every minute.'}),('Search & social',{'fields':('seo_title','seo_description')}),('Record',{'fields':('created_at','updated_at','views'),'classes':('collapse',)}))
    def get_form(self,request,obj=None,**kwargs):
        base=super().get_form(request,obj,**kwargs)
        class BoundForm(base):
            def __init__(self,*args,**kw): super().__init__(*args,user=request.user,**kw)
        return BoundForm
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        return qs if request.user.has_perm('news.publish_article') else qs.filter(author=request.user)
    def get_readonly_fields(self,request,obj=None):
        fields=list(self.readonly_fields)
        if not request.user.has_perm('news.publish_article'): fields+=['author','featured','breaking','published_at']
        return fields
    def has_change_permission(self,request,obj=None):
        allowed=super().has_change_permission(request,obj)
        if obj and not request.user.has_perm('news.publish_article'):
            return allowed and obj.author_id==request.user.pk and obj.status in ('draft','review')
        return allowed
    def has_view_permission(self,request,obj=None):
        return super().has_view_permission(request,obj) and (not obj or request.user.has_perm('news.publish_article') or obj.author_id==request.user.pk)
    def has_delete_permission(self,request,obj=None):
        return request.user.has_perm('news.publish_article') and super().has_delete_permission(request,obj)
    def save_model(self,request,obj,form,change):
        if not request.user.has_perm('news.publish_article'): obj.author=request.user
        super().save_model(request,obj,form,change)
        AuditLog.objects.create(actor=request.user,action=f'Saved article #{obj.pk}: {obj.title} ({obj.status})')
    def delete_model(self,request,obj):
        AuditLog.objects.create(actor=request.user,action=f'Deleted article #{obj.pk}: {obj.title}')
        super().delete_model(request,obj)
    def delete_queryset(self,request,queryset):
        for obj in queryset: AuditLog.objects.create(actor=request.user,action=f'Deleted article #{obj.pk}: {obj.title}')
        super().delete_queryset(request,queryset)
    @admin.display(description='Preview')
    def preview_link(self,obj):
        return format_html('<a href="{}">Preview story ↗</a>',reverse('newsroom:preview',args=[obj.pk])) if obj.pk else 'Save a draft to preview.'

@admin.register(Media,site=site)
class MediaAdmin(admin.ModelAdmin):
    list_display=('thumbnail','title','alt_text','uploaded_by','created_at')
    search_fields=('title','alt_text','caption')
    readonly_fields=('thumbnail','uploaded_by','created_at')
    def get_queryset(self,request):
        qs=super().get_queryset(request)
        return qs if request.user.has_perm('news.publish_article') else qs.filter(uploaded_by=request.user)
    def save_model(self,request,obj,form,change):
        if not change: obj.uploaded_by=request.user
        super().save_model(request,obj,form,change)
        AuditLog.objects.create(actor=request.user,action=f'Saved media #{obj.pk}: {obj.title}')
    def thumbnail(self,obj):
        return format_html('<img src="{}" alt="{}" width="100">',obj.image.url,obj.alt_text) if obj.image else 'No image'

@admin.register(Category,site=site)
class CategoryAdmin(admin.ModelAdmin):
    list_display=('name','slug','order')
    prepopulated_fields={'slug':('name',)}
    search_fields=('name',)
@admin.register(Tag,site=site)
class TagAdmin(admin.ModelAdmin): search_fields=('name',)
@admin.register(AuditLog,site=site)
class AuditAdmin(admin.ModelAdmin):
    list_display=('created_at','actor','action')
    readonly_fields=('created_at','actor','action')
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(ArticleView,site=site)
class ViewAdmin(admin.ModelAdmin):
    list_display=('article','day','count')
    list_filter=('day',)
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
@admin.register(Subscriber,site=site)
class SubscriberAdmin(admin.ModelAdmin):
    list_display=('email','confirmed','created_at')
    search_fields=('email',)
    readonly_fields=('email','confirmed','created_at')
    def has_add_permission(self,request): return False
@admin.register(ContactMessage,site=site)
class ContactAdmin(admin.ModelAdmin):
    list_display=('name','email','created_at','resolved')
    readonly_fields=('name','email','message','created_at')
    list_filter=('resolved',)
    def has_add_permission(self,request): return False
@admin.register(SiteSettings,site=site)
class SettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self,request): return not SiteSettings.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self,request,obj=None): return False
site.register(User,UserAdmin)
site.register(Group,GroupAdmin)

from django.contrib.admin.models import LogEntry
@admin.register(LogEntry,site=site)
class ActionHistoryAdmin(admin.ModelAdmin):
    list_display=('action_time','user','content_type','object_repr','action_flag')
    list_filter=('action_flag','content_type','user')
    search_fields=('object_repr','change_message')
    readonly_fields=('action_time','user','content_type','object_id','object_repr','action_flag','change_message')
    def has_module_permission(self,request): return request.user.is_superuser
    def has_view_permission(self,request,obj=None): return request.user.is_superuser
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
