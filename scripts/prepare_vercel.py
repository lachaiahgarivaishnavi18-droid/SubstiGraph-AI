"""Stage only deployable source, excluding local databases, caches and tooling."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
target = root / '.runtime' / 'vercel-source'
target.mkdir(parents=True, exist_ok=True)
for name in ('app.py', 'requirements.txt', 'pyproject.toml', 'vercel.json', '.vercelignore'):
    shutil.copy2(root / name, target / name)
for name in ('backend/app', 'frontend/src'):
    shutil.copytree(root / name, target / name, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
(target / 'backend').mkdir(exist_ok=True)
shutil.copy2(root / 'backend/requirements-vercel.txt', target / 'backend/requirements-vercel.txt')
for name in ('package.json','pnpm-lock.yaml','pnpm-workspace.yaml','index.html',
             'tsconfig.json','vite.config.ts','tailwind.config.js','postcss.config.js'):
    shutil.copy2(root / 'frontend' / name, target / 'frontend' / name)
print(target)
