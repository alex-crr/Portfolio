Portfolio of Alexandre Courrieu: https://alex.courri.eu (main), https://alex.courri.eu/beta/ (dev).

Projects live in `projects/`, one TOML file each; copy `projects/_template.toml` to add one.
Then run `python3 design/build.py` (Python 3.11+): it checks the files and rebuilds `index.html`.
Pushing to `main` or `dev` also rebuilds and deploys (`.github/workflows/pages.yml`).
The page itself is `design/portfolio.dc.html`.
