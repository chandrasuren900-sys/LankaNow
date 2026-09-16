from django.urls import path,re_path
from django.shortcuts import redirect
from django.contrib.auth import views as auth
from news import views
from news.admin import site

def legacy_admin(request,filename):
    mapping={'dashboard':'/admin/','editor':'/admin/news/article/add/','articles':'/admin/news/article/','categories':'/admin/news/category/','media':'/admin/news/media/','users':'/admin/auth/user/','analytics':'/admin/analytics/','settings':'/admin/news/sitesettings/','login':'/admin/login/'}
    return redirect(mapping.get(filename,'/admin/'))
urlpatterns=[
    path('',views.home,name='home'),path('index.html',lambda r:redirect('home')),
    path('search/',views.listing,name='search'),path('search.html',lambda r:redirect('/search/')),
    path('article/<str:slug>/',views.article,name='article'),
    path('about/',views.info,{'page':'about'},name='about'),path('privacy/',views.info,{'page':'privacy'},name='privacy'),path('terms/',views.info,{'page':'terms'},name='terms'),path('contact/',views.contact,name='contact'),
    re_path(r'^(?P<page>about|privacy|terms)\.html$',lambda r,page:redirect('/'+page+'/')),
    path('contact.html',lambda r:redirect('contact')),
    path('newsletter/subscribe/',views.subscribe,name='subscribe'),path('newsletter/confirm/<str:token>/',views.confirm),path('newsletter/unsubscribe/<str:token>/',views.unsubscribe),
    path('api/articles/',views.api_articles),path('sitemap.xml',views.sitemap),path('robots.txt',views.robots),path('media/images/<str:filename>',views.media),
    path('admin-login.html',lambda r:redirect('/admin/login/')),
    re_path(r'^admin/(?P<filename>[a-z]+)\.html$',legacy_admin),
    path('admin/',site.urls),
    path('accounts/password-reset/',views.PasswordResetView.as_view(),name='password_reset'),
    path('accounts/password-reset/done/',auth.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/',auth.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'),name='password_reset_confirm'),
    path('accounts/reset/done/',auth.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),name='password_reset_complete'),
    re_path(r'^pages/(?P<slug>[a-z]+)\.html$',lambda r,slug:redirect('/'+slug+'/')),
    path('<slug:slug>/',views.listing,name='category'),
]
