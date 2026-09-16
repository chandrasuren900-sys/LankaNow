# Production deployment

The included Windows launcher is for local use. Do not expose Django’s development server publicly.

## Required infrastructure

- Python 3.12+ Linux service or the included Docker image.
- PostgreSQL, an HTTPS reverse proxy/load balancer and a real hostname.
- Persistent storage mounted at `/app/media` in Docker. The media folder must not be served directly by the proxy: the application enforces published/staff-only access.
- Scheduled execution of `python manage.py publish_due` once per minute.
- SMTP provider for password recovery and newsletter confirmation.
- Database and media backups with restoration drills.

## Environment

`.env.example` lists the configuration variables. Django does not load that file automatically. Export variables in the service environment or pass it through Docker `--env-file` after replacing the example values. Keep secrets out of source control.

Generate `DJANGO_SECRET_KEY` on the server with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS` to actual hostnames, `SITE_URL` to the canonical HTTPS origin, and `CSRF_TRUSTED_ORIGINS` to the exact HTTPS origins. Set `DATABASE_URL` to a PostgreSQL connection string. Ensure the database is reachable only by the application.

Set `TRUST_PROXY=1` only if the app is reachable exclusively through a trusted proxy that **removes incoming X-Forwarded-Proto and sets its own value**. The app otherwise does not trust proxy headers. Restore the real client address at the trusted server boundary for per-client rate limits; do not copy arbitrary user-supplied forwarding headers. Without correct client IP restoration, application throttling may share a bucket across users behind one proxy. Add edge login/contact rate limiting as defense in depth.

## Initialize and run

In the configured production environment:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py setup_newsroom
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py check --deploy
python -m gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --access-logfile - --error-logfile -
```

Use systemd or your hosting platform’s process manager to restart the service after failure. Container deployments bind to `0.0.0.0:8000` inside their private container network. Connect the reverse proxy to this port; do not expose it directly to the internet.

WhiteNoise serves versioned compressed static assets. Uploaded media is routed through Django. Enforce a request size limit around 6 MB at the proxy for upload routes. Protect logs because query strings may contain searches or signed newsletter tokens. Never log passwords, cookies or POST bodies.

## Scheduled publishing

Create a cron/platform job every minute using the same environment and database as the web service:

```text
* * * * * /path/to/venv/bin/python /path/to/LankaNow/manage.py publish_due
```

The scheduler locks due article rows inside a transaction on PostgreSQL, updates publication status and records an audit event. It also clears expired throttling buckets. The web process does not pretend scheduling is active when no scheduler is running. Monitor job failures. The local launcher runs this command automatically for local testing only.

## Backups and restore

- Back up PostgreSQL daily with `pg_dump --format=custom` to an encrypted, separate location; keep a retention policy suited to your newsroom.
- Back up the `media/` tree at the same cadence and before infrastructure changes.
- Preserve the production secret securely; changing it invalidates sessions and signed links.
- Before a release, take a backup, install dependencies, run tests, apply migrations, collect static files, then restart services.
- Restore a backup into an isolated PostgreSQL database with `pg_restore`, restore matching media files, point an isolated app at it, and verify article text, images, staff login and scheduler behavior. Perform this drill periodically.
- For local SQLite, stop the launcher before copying `db.sqlite3` and `media/` together. Do not back up a live SQLite file with a naive copy.

Media deletion removes the database record; unused underlying files are intentionally retained to avoid accidental data loss. Establish a reviewed orphan-file retention/cleanup process before large-scale use.

## Before going live

- Create your real staff accounts with least privilege; test Author versus Admin behavior.
- Review publication identity, contact details, privacy notice and terms.
- Add verified news and images you have permission to publish.
- Verify SMTP delivery, recovery links and newsletter confirmation/unsubscribe on the actual hostname.
- Confirm HTTPS, secure cookies, CSRF origins, scheduler, backups and error monitoring.
- Run `check --deploy` using the actual production variables; investigate warnings.
- Run a separate penetration/security review and load test for the actual hosting environment. Passing included tests is not a security certification.
- Review dependency advisories and update the pinned versions regularly. The dependency file records the versions installed during this build.

## Troubleshooting

- **DisallowedHost:** update `DJANGO_ALLOWED_HOSTS` to your real domain, without scheme or paths.
- **CSRF verification failed:** use the correct HTTPS origin, configure `CSRF_TRUSTED_ORIGINS`, and verify trusted proxy headers.
- **Redirect loop:** fix proxy HTTPS forwarding; do not disable HTTPS protection as a shortcut.
- **No scheduled story:** check the publication time (Asia/Colombo), status and scheduler logs.
- **No images:** check persistent media mount, record existence and article publication status.
- **Static CSS missing:** run `collectstatic` in the production environment before starting workers.
- **Login locked out:** wait 15 minutes; inspect reverse-proxy client IP handling if many staff share one bucket.
- **Lost administrator password:** run `python manage.py changepassword USERNAME` on the server, or use email recovery once SMTP is configured.

HSTS preload is deliberately opt-in. `check --deploy` reports W021 while `HSTS_PRELOAD` is unset. Set `HSTS_PRELOAD=1` only after deciding to commit the domain and subdomains to HTTPS preload requirements. The setting does not itself submit the domain to a browser preload list.
