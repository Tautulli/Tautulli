pybabel extract -F babel.cfg -o tautulli.pot --charset=utf-8 --sort-output --copyright-holder=Tautulli ../..
pybabel compile -D tautulli -d . -l en