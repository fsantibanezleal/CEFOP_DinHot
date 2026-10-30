# Deploy: GitHub Pages

The site and its committed artifacts are served statically. `.github/workflows/deploy-pages.yml` runs after CI
succeeds on `main`, on that commit: it checks the committed artifacts, builds the site with its base path, deploys,
and checks the live site (`scripts/check_live.py`). It never rebakes, trains or recomputes.

## Once per product, before the first deploy

1. Enable Pages with GitHub Actions as the source:
   `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`
2. With a custom domain, `scripts/instantiate.py --domain` wrote a CNAME file into `frontend/public/`; set the domain on the
   repository as well (the file alone does not set it for an Actions deploy):
   `gh api -X PUT repos/<owner>/<repo>/pages -f cname=<sub>.fasl-work.com`
3. Create the DNS record as a CNAME to `<owner>.github.io`, DNS only (not proxied), so GitHub can issue the
   certificate; enforce HTTPS once it is issued:
   `gh api -X PUT repos/<owner>/<repo>/pages -F https_enforced=true`

Without a custom domain the site is a project page at `https://<owner>.github.io/<repo>/`, and the deploy builds
with that base path.
