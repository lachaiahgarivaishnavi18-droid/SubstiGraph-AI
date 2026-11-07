"""Vercel entrypoint: REST API and React build share a single origin."""
from pathlib import Path
from backend.app.main import app

app.frontend(
    '/',
    directory=Path(__file__).parent / 'frontend' / 'dist',
    fallback='index.html',
)
