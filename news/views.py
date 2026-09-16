import json, logging
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q,F,Sum,FloatField,ExpressionWrapper,Value
from django.utils import timezone
from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.contrib import messages
from django.views.decorators.http import require_POST,require_GET
from django.contrib.auth import views as auth_views
from .models import *
from .forms import *
from .middleware import limited

def public_articles(): return Article.objects.published().select_related('category','author','featured_image').prefetch_related('tags')
def trending():
    # Seven-day views plus lifetime count with recency decay, computed from real counts.
    recent=public_articles().annotate(week_views=Sum('articleview__count',filter=Q(articleview__day__gte=timezone.localdate()-timedelta(days=7)),default=0))
    return sorted(recent,key=lambda a:(a.week_views*3+a.views*.1+1)/((timezone.now()-a.published_at).total_seconds()/3600+2)**1.25,reverse=True)[:10]
def home(request):
    articles=public_articles()
    hero=articles.filter(featured=True).first() or articles.first()
    latest=articles.exclude(pk=hero.pk)[:6] if hero else []
    sections=[(c,list(articles.filter(category=c)[:3])) for c in Category.objects.all()]
    return render(request,'news/home.html',{'hero':hero,'latest':latest,'trending':trending()[:5],'breaking':articles.filter(breaking=True)[:4],'sections':sections})
def listing(request,slug=None):
    q=request.GET.get('q','').strip()[:200]
    category=get_object_or_404(Category,slug=slug) if slug else None
    articles=public_articles()
    title=category.name if category else 'Search'
    if category: articles=articles.filter(category=category)
    if slug=='trending': articles=trending()
    if q:
        articles=public_articles().filter(Q(title__icontains=q)|Q(content__icontains=q)|Q(summary__icontains=q)|Q(category__name__icontains=q)|Q(tags__name__icontains=q)|Q(author__username__icontains=q)|Q(author__first_name__icontains=q)|Q(author__last_name__icontains=q)).distinct()
    elif not category: articles=Article.objects.none()
    page=Paginator(articles,12).get_page(request.GET.get('page'))
    return render(request,'news/listing.html',{'title':title,'category':category,'query':q,'page':page,'trending':trending()[:4]})
def article(request,slug):
    a=get_object_or_404(public_articles(),slug=slug)
    if request.method=='GET':
        Article.objects.filter(pk=a.pk).update(views=F('views')+1)
        counter,_=ArticleView.objects.get_or_create(article=a,day=timezone.localdate())
        ArticleView.objects.filter(pk=counter.pk).update(count=F('count')+1)
    schema={'@context':'https://schema.org','@type':'NewsArticle','headline':a.title,'description':a.summary,'datePublished':a.published_at.isoformat(),'dateModified':a.updated_at.isoformat(),'author':{'@type':'Person','name':a.author.get_full_name() or a.author.username},'publisher':{'@type':'Organization','name':'LankaNow'},'mainEntityOfPage':settings.SITE_URL+a.get_absolute_url()}
    if a.featured_image: schema['image']=[settings.SITE_URL+a.featured_image.image.url]
    schema={'@context':'https://schema.org','@graph':[schema,{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':settings.SITE_URL+'/'},{'@type':'ListItem','position':2,'name':a.category.name,'item':settings.SITE_URL+a.category.get_absolute_url()},{'@type':'ListItem','position':3,'name':a.title,'item':settings.SITE_URL+a.get_absolute_url()}]}]}
    schema_json=json.dumps(schema).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return render(request,'news/article.html',{'article':a,'schema_json':schema_json,'related':public_articles().filter(category=a.category).exclude(pk=a.pk)[:3],'latest':public_articles().exclude(pk=a.pk)[:4]})
def info(request,page):
    if page not in ['about','privacy','terms']: raise Http404
    return render(request,'news/info.html',{'page_name':page,'title':page.title()})
def contact(request):
    form=ContactForm(request.POST or None)
    if request.method=='POST':
        if limited(request,'contact',5): return HttpResponse('Please try again in 15 minutes.',status=429)
        if form.is_valid():
            form.save(); messages.success(request,'Your message has been sent to the newsroom.'); return redirect('contact')
    return render(request,'news/contact.html',{'form':form,'title':'Contact'})
@require_POST
def subscribe(request):
    if limited(request,'subscribe',5): return HttpResponse('Please try again in 15 minutes.',status=429)
    form=SubscribeForm(request.POST)
    if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
        messages.error(request,'Newsletter signup is not available yet.'); return redirect('home')
    if form.is_valid():
        email=form.cleaned_data['email'].lower()
        token=signing.dumps(email,salt='newsletter')
        try:
            send_mail('Confirm your LankaNow newsletter signup','Confirm your subscription: '+settings.SITE_URL+'/newsletter/confirm/'+token+'/',settings.DEFAULT_FROM_EMAIL,[email])
            Subscriber.objects.get_or_create(email=email)
            messages.success(request,'Check your email to confirm your subscription.')
        except Exception:
            logging.getLogger(__name__).exception('Newsletter email delivery failed')
            messages.error(request,'We could not send the confirmation email. Please try again later.')
    else: messages.error(request,'Enter a valid email and agree to receive the newsletter.')
    return redirect('home')
def confirm(request,token):
    try: email=signing.loads(token,salt='newsletter',max_age=172800)
    except signing.BadSignature: return HttpResponse('This confirmation link has expired or is invalid.',status=400)
    if request.method=='POST':
        Subscriber.objects.filter(email=email).update(confirmed=True)
        messages.success(request,'Your newsletter subscription is confirmed.'); return redirect('home')
    return render(request,'news/confirm.html',{'title':'Confirm subscription'})
def unsubscribe(request,token):
    try: email=signing.loads(token,salt='unsubscribe')
    except signing.BadSignature: return HttpResponse('Invalid link.',status=400)
    if request.method=='POST':
        Subscriber.objects.filter(email=email).delete()
        messages.success(request,'You have been unsubscribed.'); return redirect('home')
    return render(request,'news/confirm.html',{'title':'Unsubscribe'})
@require_GET
def api_articles(request):
    qs=public_articles()
    if request.GET.get('category'): qs=qs.filter(category__slug=request.GET['category'])
    page=Paginator(qs,20).get_page(request.GET.get('page'))
    return JsonResponse({'count':page.paginator.count,'page':page.number,'pages':page.paginator.num_pages,'results':[{'id':a.pk,'title':a.title,'slug':a.slug,'summary':a.summary,'category':a.category.name,'published_at':a.published_at.isoformat(),'url':a.get_absolute_url()} for a in page]})
def sitemap(request):
    from xml.sax.saxutils import escape
    paths=['/','/about/','/contact/']+[c.get_absolute_url() for c in Category.objects.all()]+list(public_articles().values_list('slug',flat=True))
    urls=['<url><loc>'+escape(settings.SITE_URL+(p if p.startswith('/') else '/article/'+p+'/'))+'</loc></url>' for p in paths]
    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(urls)+'</urlset>',content_type='application/xml')
def robots(request): return HttpResponse('User-agent: *\nDisallow: /admin/\nDisallow: /accounts/\nDisallow: /search/\nSitemap: '+settings.SITE_URL+'/sitemap.xml',content_type='text/plain')
def media(request,filename):
    asset=get_object_or_404(Media,image='images/'+filename)
    if not (request.user.is_active and request.user.is_staff) and not Article.objects.published().filter(featured_image=asset).exists(): raise Http404
    response=FileResponse(asset.image.open('rb'),content_type='image/webp')
    response['Cache-Control']='private, max-age=300'
    return response
class PasswordResetView(auth_views.PasswordResetView):
    template_name='registration/password_reset_form.html'
    email_template_name='registration/password_reset_email.txt'
    success_url='/accounts/password-reset/done/'
    def form_valid(self,form):
        if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
            form.add_error(None,'Password recovery email is not configured. Ask the server administrator to reset your password.'); return self.form_invalid(form)
        try: return super().form_valid(form)
        except Exception:
            logging.getLogger(__name__).exception('Password reset email failed')
            form.add_error(None,'Email is temporarily unavailable. Please try again later.'); return self.form_invalid(form)
