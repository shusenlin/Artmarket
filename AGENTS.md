# Repository Guidelines

## Project Structure & Module Organization

This is a Flask application for artwork registration, artist profiles, comments, user profiles, and an AI appraisal assistant.

- `app.py`: application factory, blueprint registration, development SQLite schema compatibility.
- `models.py`: SQLAlchemy models for users, artworks, artists, comments, and transactions.
- `blueprints/`: route modules grouped by feature (`auth.py`, `artworks.py`, `profile.py`, `owner.py`, `assistant.py`).
- `templates/`: Jinja templates grouped by page area; shared fragments live in `templates/components/`.
- `static/css/` and `static/js/`: frontend styling and page scripts.
- `static/uploads/`: local uploaded media during development.
- `instance/`: local SQLite database files; do not commit runtime database contents.
- `docs/` and `scripts/`: deployment notes and helper scripts.

## Build, Test, and Development Commands

Create and activate the existing conda environment, then install dependencies:

```bash
source /home/forest/miniconda3/bin/activate artmarket
pip install -r requirements.txt
```

Run locally:

```bash
python app.py
```

Basic validation:

```bash
python -m compileall app.py models.py blueprints
node --check static/js/main.js
node --check static/js/assistant.js
```

Use `pkill -f "python app.py"` before restarting if an old Flask process is still running.

## Coding Style & Naming Conventions

Use 4-space indentation for Python. Keep route handlers focused and place reusable helpers near the blueprint that owns them. Model classes use `PascalCase`; columns, helper functions, routes, and template variables use `snake_case`. Keep Jinja templates readable and prefer shared includes, such as `templates/components/nav_links.html`, for repeated UI.

Frontend code uses plain JavaScript and CSS. Keep selectors descriptive and scoped by component where possible, for example `.artist-manage-card` or `.ai-assistant-panel`.

## Testing Guidelines

There is no formal test suite yet. For changes, run compile checks and add small Flask test-client smoke checks when touching routes, database models, authentication, uploads, or permissions. Test both authenticated and guest flows where relevant. Use temporary in-memory/testing databases instead of editing `instance/artmarket.db` directly.

## Commit & Pull Request Guidelines

This repository currently has no commit history. Use short, imperative commit messages, for example:

```text
Add artist profile review workflow
Fix assistant chat storage isolation
```

Pull requests should include a concise summary, affected pages/routes, verification commands, and screenshots for visible UI changes.

## Security & Configuration Tips

Never commit real `.env` secrets or API keys. Use `.env.example` for placeholders. `ARK_API_KEY` must be available to the running Flask process. Uploaded files and SQLite data under `static/uploads/` and `instance/` are local runtime artifacts and should be treated as development data.
