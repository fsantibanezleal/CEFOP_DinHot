# deploy/

`TARGET` names the product's one deploy place: `pages` or `vps` (`scripts/check_deploy_place.py`).

- `pages.md`: GitHub Pages, a static site, driven by `.github/workflows/deploy-pages.yml`.
- `fasl-slug.service` and `domain.nginx`: the VPS unit and site templates, for a product with an active backend
  (`app/`). `scripts/instantiate.py` keeps the files of the chosen place only, and fills the slug and the domain.
