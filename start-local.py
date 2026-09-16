"""Local development launcher. Never use this script as the public production server."""
import os,sys,subprocess,threading,time
from pathlib import Path
os.chdir(Path(__file__).resolve().parent)
os.environ['DJANGO_DEBUG']='1'
os.environ.setdefault('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1,[::1]')
def run(*args): subprocess.run([sys.executable,'manage.py',*args],check=True)
run('migrate');run('setup_newsroom')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    print('\nCreate your own administrator account. Choose a unique password of at least 12 characters.\n')
    run('createsuperuser')
def schedule():
    while True:
        try: run('publish_due')
        except Exception as e: print('Scheduler error:',e)
        time.sleep(60)
threading.Thread(target=schedule,daemon=True).start()
print('\nPublic website: http://127.0.0.1:8000/\nNewsroom: http://127.0.0.1:8000/admin/\nPress Ctrl+C to stop.\n')
run('runserver','127.0.0.1:8000','--noreload')
