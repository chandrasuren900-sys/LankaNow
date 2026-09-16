# LankaNow — Know Now.

A complete runnable Django media application with a responsive public website and a separate authenticated newsroom. This package replaces the static HTML/localStorage prototype; it is **not** a file that can run by double-clicking index.html.

## Start on Windows

1. Extract the entire ZIP into a new folder. Keep the original prototype as a backup.
2. Install Python 3.12 or newer from https://www.python.org/downloads/ if needed. Enable the Python launcher during installation.
3. Double-click **START-WINDOWS.bat**. Internet access is required for the first dependency installation.
4. Follow the terminal prompts to create your own administrator username, email and password. Password typing is intentionally invisible. Use at least 12 characters. Do not bypass password validation.
5. Keep the terminal window open. Visit **http://127.0.0.1:8000/**.
6. Open **http://127.0.0.1:8000/admin/** directly to sign into the newsroom.

There are no supplied administrator credentials. Run the same launcher again to return to your existing database. Press Ctrl+C to stop. A browser refresh reloads the site. The launcher also checks scheduled articles every minute while running.

For macOS/Linux: run `bash start-macos-linux.sh` from this folder.

## Your first article

1. Sign into `/admin/`. Choose **Create article**.
2. Enter headline, slug, category, author, summary and body. Separate body paragraphs with a blank line. Unicode text is supported, including Sinhala and Tamil. The body is deliberately plain text; submitted HTML is escaped.
3. In Media, upload a JPEG, PNG or WebP (up to 5 MB and 24 megapixels), with alt text. Select it as the article’s featured image. Caption and credit come from the selected media record.
4. Save as **Draft**, then use **Preview story**. The preview is staff-only and does not increase public view counts.
5. Save as **In review**, or publish using an account with publishing permission.
6. For immediate publication, choose **Published** and leave publication date/time blank. For scheduling, choose **Scheduled** and set a future date/time. All newsroom times use Asia/Colombo.
7. A published article appears automatically on the homepage, category page, search, sitemap and read-only API. Featured articles lead the homepage. Breaking articles populate the breaking bar. Uncheck Breaking to remove that status.
8. To unpublish, change the status to Draft or Archived. Deletion requires the admin confirmation page.

The public website contains no admin/editor links. This separation is enforced by server-side sessions and permissions, not merely by hiding buttons.

## Staff roles

Create users as a superuser, check **Staff status**, and assign exactly one intended group. Keep **Superuser status** off for ordinary staff.

| Role | Permissions |
|---|---|
| Superuser | Full publishing, settings, users and role administration |
| Admin | Publication management, publishing/scheduling, categories, media, analytics, contact messages and subscribers; cannot administer staff privileges |
| Editor | Create/edit own drafts and review submissions; cannot publish |
| Author | Create/edit own drafts and submit for review; cannot publish |
| Reporter | Create/edit own drafts and submit for review; cannot publish |

The three non-publishing groups start with the same conservative permissions. Editors do not automatically edit other users’ stories. Grant `Can publish and schedule articles` only to trusted publishers; in this implementation that permission also grants cross-author article visibility and editing. Only a superuser manages users and groups to prevent privilege escalation.

Non-publishers cannot modify a story once it is published, scheduled or archived. A publisher must return it to draft first. Django’s standard user and group permission screens allow deliberate role adjustments.

## Included functionality

- Responsive charcoal/white/deep-red editorial design; accessible forms, mobile navigation and empty states.
- All 12 categories: News, Trending, People, Viral, Sports, Entertainment, Jobs, Deals, Events, Food, Travel and Tech.
- Dynamic homepage, article pages, related/latest stories, category pagination and database search across title, summary, body, category, tags and author.
- Protected newsroom dashboard with database counts, article filters, SEO fields, author selection, media library, categories, tags, user administration and settings.
- Draft/review/published/scheduled/archived workflow, private previews and audited article changes.
- Hashed passwords, Django database sessions, logout, CSRF protection, login/reset rate limits, server-side ownership/role checks and password reset views.
- Image content validation and re-encoding to WebP; random filenames; metadata stripped; draft-only media unavailable anonymously.
- Real article GET counts and daily/category reports. These include repeated visits and bots. They are **not unique visitors**.
- Trending score: `(7-day views × 3 + lifetime views × 0.1 + 1) / (age in hours + 2)^1.25`. Results are based on database values, never random.
- Read-only paginated `/api/articles/`, `/sitemap.xml`, `/robots.txt`, canonical/OG/X tags and article/breadcrumb structured data.
- Contact form messages saved to the newsroom; newsletter confirmation/unsubscribe and a command-line mail sender.
- Database migrations, PostgreSQL configuration, Dockerfile, production instructions and security regression tests.

Legacy `/pages/news.html`-style paths redirect to category URLs. `/admin/editor.html` redirects to the protected editor. Old localStorage articles are not silently trusted or copied.

## Email and newsletter

SMTP is not connected in this download. The site clearly displays “Coming soon” for the newsletter until SMTP configuration is present. No successful subscription is fabricated. Password recovery explains when email is unavailable; the server owner can always use `python manage.py changepassword USERNAME`.

Set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` on the server. A newsletter registration sends a signed confirmation link; the reader must confirm with a form submission. Only confirmed subscribers receive newsletters.

Prepare a UTF-8 text file, then preview recipient count:

```bash
python manage.py send_newsletter --subject "The LankaNow Letter" --body-file newsletter.txt
```

Append `--send` only when ready to email subscribers. The command sends separate messages with signed unsubscribe links. It is a simple synchronous sender, not a bulk-email queue; configure a transactional email provider and a queue before large-scale campaigns. If a send fails mid-batch, inspect provider logs before retrying to avoid duplicate deliveries.

## Content and publication settings

Open News → Publication settings in the newsroom to edit the about text, contact email, privacy text and terms. Review these with your actual company details and data practices before public launch. The starter copy is not a jurisdiction-specific legal policy.

No fabricated news stories, stock-photo claims, fake statistics or demo credentials are included. Empty sections fill automatically when your team publishes articles. A public news website needs your verified reporting and licensed images; the ZIP does not scrape or invent them.

## Importing existing prototype articles (optional)

Browser localStorage lives in the browser, not inside the old ZIP. If you have stories there, export the value of `lankaNowArticles` to a JSON file using your browser’s developer tools. Then run:

```bash
python manage.py import_prototype old-articles.json --author YOUR_STAFF_USERNAME
```

The importer creates drafts only, skips existing slugs, ignores publication flags and does not import passwords or remote images. Review text and upload images in the newsroom. HTML from the prototype displays as escaped text; clean it up before publishing.

## Tests

Activate your virtual environment, set `DJANGO_DEBUG=1` in your shell, and run:

```bash
python manage.py test news
python manage.py check
```

See **VALIDATION.md** for the checks executed on this package. See **DEPLOYMENT.md** before hosting it publicly.

## Important limits

This is an implemented and tested application package, not an already deployed or independently security-audited service. The local launcher binds to your computer only. Production still requires a domain, TLS, a production server/database, persistent media storage, scheduled jobs, backups, SMTP configuration and editorial/legal review. There are no comments, automatic translations, ad manager, payment processing or external news feeds. Jobs, Deals and Events are editorial categories, not separate marketplace booking systems.

Local SQLite is a real persistent database and is suitable for initial single-machine use. Use PostgreSQL and persistent storage for production. The app performs portable database search; add PostgreSQL full-text indexes and precomputed trending at larger catalogue sizes. Media files are served by the app with publication checks; a high-volume deployment should move them behind a publication-aware object-storage/CDN design.

## Reference documentation

The implementation uses Django’s maintained authentication, admin, forms, ORM and security middleware. Production reference: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ and https://docs.djangoproject.com/en/5.2/topics/security/.
