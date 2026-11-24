Portfolio of Alexandre Courrieu: https://alex.courri.eu (main), https://alex.courri.eu/beta/ (dev).

Projects live in `projects/`, one TOML file each holding everything about that project;
`projects/_template.toml` is the commented reference, copy it to add one.
Then run `python3 design/build.py` (Python 3.11+): it derives column numbers, the PERIOD row and
FIG. numbers, refuses inconsistent files (listing every error), and rebuilds `index.html`.
Pushing to `main` or `dev` also rebuilds and deploys (`.github/workflows/pages.yml`).
The page itself is `design/portfolio.dc.html`.
