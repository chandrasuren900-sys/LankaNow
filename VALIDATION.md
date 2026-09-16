# Validation record

## Executed checks

- **28 Django tests passed** on the SQLite test backend.
- Anonymous and non-staff admin access denied; legacy editor redirect ends at login.
- Non-publishers cannot forge publication status, edit another author’s draft, preview another author’s draft, or modify a published article.
- Authorized publisher creates a live article; scheduling publishes due stories and leaves future stories private.
- Drafts excluded from articles, search, API and sitemap.
- Article content and dangerous headline text escaped; SQL-like search strings handled through the ORM.
- CSRF enforcement rejects missing-token writes; API rejects POST; login attempts throttled; logout invalidates access.
- Disguised non-image upload rejected; valid PNG re-encoded to WebP; unpublished media not publicly accessible.
- Real article view counts increment; contact messages persist.
- SMTP-disabled signup does not fabricate success. Newsletter confirmation/unsubscribe and password recovery tested with Django’s in-memory email backend, not a real SMTP provider.
- Unicode article route, group configuration preservation, public routes and newsroom pages checked.
- Database migrations apply; Django system checks pass.
- Static asset collection and compression complete successfully.
- Production settings checked with a temporary secret and HTTPS example hostname. Only W021 (optional HSTS preload) remains under default settings; this decision is documented in DEPLOYMENT.md.

## Browser checks

Executed with headless Chromium at **1440 × 1000** and **390 × 844**:

- Desktop/mobile homepage screenshots visually reviewed.
- Mobile menu opens and navigates to Sports.
- Staff login, dashboard and editor render.
- No horizontal overflow on homepage or mobile editor; no browser JavaScript errors during that flow.
- End-to-end browser journey passed: login → save draft → private preview → publish → anonymous article → search → breaking bar → archive → public 404.
- Desktop/mobile article layout screenshots captured using clearly labeled temporary layout-test content. No horizontal overflow on mobile article.
- Mobile hero typography and discovery-strip spacing adjusted following visual review.

The `previews/` folder contains screenshots. The username shown there was used only in the temporary QA database. That database, its account, secret, sessions and test article are excluded from the package. Screenshots of test articles are labeled as layout tests, not news reports.

## Not verified in this environment

- Actual Windows batch execution (the Python application was run and tested on Linux).
- PostgreSQL under production traffic; configuration and driver included, database tests used SQLite.
- Docker image build or live infrastructure deployment.
- Real SMTP delivery or email-provider reputation.
- Domain/TLS/reverse proxy configuration on your hosting account.
- External penetration testing, large-scale load testing or formal Core Web Vitals certification.

These require your actual infrastructure. Passing this test suite is not a claim that every possible defect or security risk has been eliminated.
