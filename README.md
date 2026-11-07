# SubstiGraph AI

A working local retail application with a React/TypeScript interface, FastAPI REST API, SQLAlchemy persistence, evidence-derived knowledge graph, compatible-product ranking, and constrained assortment optimization.

The supplied request ended mid-sentence in section 8. This implementation follows the available requirements. All 600 seeded products are **synthetic**, use USD, span five categories, ten subcategories, six brands and twelve suppliers. No observed customer behavior or experimentally validated recommendation accuracy is claimed.

## Run locally

Use Python 3.12+ and Node 22+. Commands below are PowerShell, from this project directory. This workspace has a prepared `.venv` and installed frontend dependencies. The development API uses port **8010** because another application occupies port 8000 on this machine.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

In a second terminal:

```powershell
cd frontend
pnpm install
pnpm dev
```

Open the Local URL printed by Vite (normally http://localhost:5173). Existing apps may occupy ports 5173/5174; Vite selects the next free port. The `/api` development proxy targets port 8010. REST documentation: http://127.0.0.1:8010/docs.

If a package manager wrapper interferes with commands, run tools directly:

```powershell
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
node node_modules/vite/bin/vite.js --host 127.0.0.1
```

SQLite is created in the backend working directory and persists across restarts. Empty databases are seeded once; existing records are preserved. Environment configuration is read from the process; `.env.example` documents keys but the local server does not automatically load it. For example `$env:GRAPH_BACKEND='networkx'` before starting Uvicorn.

After dependency installation, `powershell -ExecutionPolicy Bypass -File .\start.ps1` starts both services in hidden background processes on ports 8010 and 5175, with logs under `.runtime/`. Run `.\stop.ps1` to stop those saved processes. The start script rejects occupied ports and the stop script checks process creation times before stopping anything.

## Features

- Dashboard with live database inventory metrics and category revenue chart.
- Product creation, full editing/detail dialog, safeguarded deletion by exact SKU, search, brand/category/price/availability filters, sorting and pagination.
- CSV export and all-or-nothing import with row-specific validation, duplicate detection, UTF-8 checking and upload limits. Exported text escapes spreadsheet formula prefixes.
- Knowledge graph visualization, inspectable nodes, relationship paths and automatic graph reconstruction after writes. Snapshot replacement keeps readers on a complete graph during rebuilds.
- Substitution engine: exact category/subcategory and recorded specification compatibility, configurable price deviation, availability and extra required specifications (API), then weighted ranking. Results include component scores, matching/differing attributes, stock, price delta, explanation and evidence IDs. Top 5, top 10 or all eligible; explicit no-match responses.
- Settings persist scoring weights in the database and require a total of 100. Defaults: attributes 30, semantic 25, category 15, price 15, availability 10, brand 5. These are initial business weights.
- PuLP/CBC binary optimization: budget, maximum SKUs, minimum per category and subcategory diversity caps. Objective is unit margin multiplied by log(1 + historical sales). One unit per chosen SKU. Infeasible/nonoptimal solves do not return unverified allocations.
- Catalog assistant with relevant record retrieval, deterministic fallback and optional OpenAI-compatible JSON generation validated with Pydantic and allowed evidence IDs. Unmatched questions return no evidence rather than unrelated records.

## AI and storage configuration

Defaults require no external credentials: `DATABASE_URL=sqlite:///./substigraph.db`, `GRAPH_BACKEND=networkx`, `SEMANTIC_MODE=tfidf`. TF-IDF is lexical similarity, **not** transformer embeddings; the active mode is visible in health and recommendations.

To enable Sentence Transformers:

```powershell
.\.venv\Scripts\python -m pip install -r backend/requirements-ai.txt
$env:SEMANTIC_MODE='sentence-transformers'
$env:EMBEDDING_MODEL='all-MiniLM-L6-v2'
```

First startup downloads the model; this requires network access. Dense embeddings and their ordered product IDs are saved under backend `data/` and regenerated on product changes. Optional `AI_ORCHESTRATION=langgraph` routes assistant retrieval and evidence validation through a LangGraph state graph. Direct mode performs the same deterministic retrieval without the optional dependency.

For generation set `LLM_API_KEY`, `LLM_BASE_URL` (base URL ending `/v1`) and `LLM_MODEL` on the backend. Only retrieved records and the question are sent to that provider. Provider errors or invalid evidence IDs return a visibly labeled deterministic fallback. Substitution explanations remain deterministic facts. JSON/citation validation does not prove all generated claims; review source records. This is catalog retrieval, not an unrestricted natural-language SQL agent.

For PostgreSQL set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/substigraph`.

For Neo4j set `GRAPH_BACKEND=neo4j`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`. Startup/writes mirror the SQL source of truth to namespaced `SubstiGraph` nodes using a transaction. Synchronization replaces only this application's graph namespace. Configure a dedicated database for each app instance. Cypher reads supply graph neighborhoods and substitution candidates; path search uses the equivalent local NetworkX snapshot. Unavailable Neo4j is reported as degraded with an explicit local fallback. It is never reported as connected after a failed synchronization.

Graph entities: products, brands, categories, subcategories, attributes, features and suppliers. All edges derive from records or exact specification compatibility. Customer segments, purchase behavior, complements, and observed competition are deliberately absent because the input contains no supporting behavioral evidence. Add validated source data before extending those relationships. Graph substitute edges express compatibility; price/stock constraints apply at recommendation time.

## API examples

```text
GET    /api/products?q=oat&available=true&sort=price&page=1&page_size=15
POST   /api/products
PUT    /api/products/{id}
DELETE /api/products/{id}?confirm_sku=SG-00001
POST   /api/products/import             multipart file
GET    /api/products/export
POST   /api/substitutes                 {"product_id":1,"max_price_deviation":0.4,"require_available":true,"limit":5}
GET    /api/graph/1
GET    /api/graph/1/path/11
POST   /api/optimize                    {"budget":5000,"max_products":30,"min_per_category":1}
POST   /api/ask                         {"question":"Which oat milk products are available?"}
GET/PUT /api/settings
GET    /api/dashboard
GET    /api/health
```

CSV columns match `ProductInput` in `backend/app/schemas.py`. Required fields: product_name, sku, brand, category, subcategory, price, cost, supplier_id. JSON columns must be quoted CSV JSON objects. Download an export as the full format reference. Imports add new SKUs; they do not silently overwrite records.

## Verification

```powershell
cd backend
..\.venv\Scripts\python -m pytest -q
cd ../frontend
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

Integration tests use an isolated temporary SQLite database. They cover seed volume, compatibility/price/stock exclusions, no-match results, ranking bounds, import atomicity, invalid weights, persisted weights, CRUD, graph updates, duplicate SKUs, deletion safeguards, feasible/infeasible optimization and source evidence. External Neo4j/PostgreSQL/LLM and transformer downloads need separately configured integration environments; they are not claimed tested by this suite.

## Deployment

`docker compose up --build` serves the frontend on http://localhost:8080 and API on port 8000 (change the host mapping if occupied). Nginx handles SPA routes and proxies `/api`; SQLite lives on a named volume. `docker compose --profile production-storage up -d postgres neo4j` starts optional storage; set the backend database/graph variables to their service hostnames to actually use them. Change development passwords before exposure.

`render.yaml` provides an alternative FastAPI deployment on Render; provide a persistent PostgreSQL `DATABASE_URL` and actual frontend `CORS_ORIGINS`. For a separate frontend-only Vercel project, choose `frontend` as root, build with `pnpm build`, output `dist`, and set `VITE_API_URL=https://YOUR_API/api` at build time. `frontend/vercel.json` handles client routes. The full-stack production deployment below uses the repository root instead.

### Full-stack Vercel deployment

Production: https://substigraph-ai.vercel.app (Vercel project `resume-project3/substigraph-ai`). A new Neon free-plan database named `substigraph-db` is connected to Production. On November 5, 2026, live checks passed for API health, 600 seeded products, 23,160 graph relationships, five ranked recommendations, constrained optimization, a temporary PostgreSQL product create/read/delete cycle, and frontend routes `/`, `/products`, and `/assistant`. Project deployment protection was preserved. The temporary verification record was removed.

The root `vercel.json`, `pyproject.toml`, and `app.py` deploy FastAPI and the React build together. Use the **repository root**, not `frontend`, for this mode. Leave `VITE_API_URL` unset; the browser calls `/api` on the same origin. Python runtime dependencies are explicitly declared in `pyproject.toml` because Vercel prioritizes it over `requirements.txt`.

Set a persistent PostgreSQL `DATABASE_URL` in the project's Production environment. Standard `postgres://` and `postgresql://` URLs are normalized to SQLAlchemy's psycopg driver. Vercel startup rejects SQLite. PostgreSQL bootstrap uses a transaction advisory lock to prevent concurrent cold starts from duplicating the synthetic seed. On Vercel, graph snapshots reload from SQL for each database-backed request so separate function instances see persisted updates. This favors correctness over performance for the demo catalog.

To deploy a clean package without local databases, caches, installed dependencies, or credentials:

```powershell
.\.venv\Scripts\python scripts/prepare_vercel.py
vercel link --yes --project substigraph-ai --cwd .runtime/vercel-source
vercel deploy --prod --yes --cwd .runtime/vercel-source
```

The staging helper preserves Vercel project identity in `.runtime/vercel-source/.vercel`; `.runtime` is excluded from Git. Never commit downloaded environment files or copy them into source. Neon can be provisioned through Vercel Marketplace and connected to Production to populate `DATABASE_URL`. Preview deployments require a separate database/environment connection before their API can start. Keep the Vercel project's existing deployment protection settings; sign in when Vercel requests it.

Alembic: from `backend`, run `alembic upgrade head` on a fresh database. The development server also creates missing initial tables automatically. For a database already initialized by startup, run `alembic stamp head`; future schema evolution should use reviewed migrations rather than `create_all`.

## Operational limits

This is a functional local reference application, not a hardened multi-tenant service. Run one backend worker; graph/embedding rebuilds are synchronous and in-memory, and large catalogs require incremental indexing, shared snapshots and queued writes. There is no authentication, authorization, rate limiting or audit log; place behind access control before external exposure. SQL is authoritative. Use backups, pinned dependency review, production migrations and load testing before business use. Compatibility is limited to recorded fields: missing specifications cannot establish real-world safety or technical interchangeability. No offline benchmark, learned demand model, customer preference inference or causal uplift claim is included.
