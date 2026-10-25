# Wind forecast desk

A web app for a UK energy utility's day-ahead buying team. It answers two questions about national (GB) wind generation, using Elexon data only:

1. **What is the latest wind forecast I can use when I have to decide?** For each delivery day D, the app shows the forecast with the newest publish time at or before a decision cutoff on D-1 (default 09:30 London time), with a 90% uncertainty band.
2. **How accurate are those forecasts?** MAE, RMSE, bias and percentile errors, broken down by forecast age, time of day and delivery day, for all purchase decisions made in January 2026 (delivery days 2 Jan to 1 Feb).

**Live app:** Add your Vercel deployment URL after deployment.

## AI tools disclosure

This project was built with the help of Claude (Anthropic's AI assistant), which generated the first draft of the backend, frontend, tests and this README. All code was reviewed, run and tested before submission.

## Data

The app reads cached Elexon data from `backend/data/` so it does not need to call the API every time a user opens the site. The current cache is labelled as Elexon data. To refresh it locally:

```bash
python -m pip install -r backend/requirements.txt
cd backend
python -m scripts.build_cache
```

The cache builder fetches January 2026 Elexon `FUELHH` wind actuals and `WINDFOR` forecasts, then updates the cache files. Use `python -m scripts.build_cache --synthetic` instead only when you explicitly want generated demo data. Include refreshed cache files in your Vercel deployment so the backend can read them. Override the Elexon URLs with `ACTUALS_URL` and `FORECAST_URL`; see `backend/app/config.py`.

## Run locally

### Docker

With Docker Desktop installed and running, start the complete app from the project root:

```bash
docker compose up --build
```

Open <http://localhost:8000>. Stop the app with Ctrl+C. The Compose configuration mounts `backend/data/` so data-cache refreshes remain in your project.

Refresh the cached Elexon data from another terminal:

```bash
docker compose run --rm app python -m scripts.build_cache
```

**Local development (two terminals)**

```bash
# Terminal 1: API (from the project root)
python -m pip install -r backend/requirements-dev.txt
python -m uvicorn app.main:app --app-dir backend --reload --port 8000

# Terminal 2: frontend (from the project root; proxies /api to port 8000)
npm --prefix frontend install
npm run dev
```

Open <http://localhost:5173>. The API is available at <http://localhost:8000>.

Run the backend tests from the project root with:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```

## Deploy to Vercel

The repository includes `vercel.json`, which configures the Vite frontend, Python API service, and `/api` routing. Import the repository in Vercel and deploy from the repository root. Ensure the files in `backend/data/` are included in the deployment; the API needs them to answer data requests. After deployment, add the public URL to the Live app link above.

## Files and directories

```
Dockerfile              builds the frontend and API into one container
docker-compose.yml      runs the container locally and persists cached data
.dockerignore           excludes generated files from the Docker build
vercel.json             Vercel frontend/backend services and API routing
package.json            root shortcuts for frontend development and build
backend/
  requirements.txt
  requirements-dev.txt  local test dependencies
  app/
    config.py           endpoints, timezone, January 2026 scope, default cutoff
    elexon.py           Elexon API client (chunked requests, retries)
    data.py             loads cached CSVs
    analysis.py         pure functions: decision-time forecast, metrics, bands (no I/O)
    service.py          joins data + analysis, shapes API responses
    main.py             FastAPI routes and optional static-file serving
  scripts/build_cache.py   fetches Elexon data into backend/data (or --synthetic demo data)
  data/                    cached forecasts, actuals, and source metadata
  tests/                   pytest: analysis, Elexon requests, API behaviour
frontend/
  package.json          Vite and React dependencies/scripts
  src/App.jsx           shell, tabs, controls
  src/DecisionView.jsx  decision clock, forecast chart with band, demand what-if
  src/AccuracyView.jsx  KPIs and four accuracy charts
  src/api.js, hooks.js, format.js, styles.css
```

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/meta` | data source, available delivery days, default cutoff |
| `GET /api/forecast?delivery_date=YYYY-MM-DD&cutoff=HH:MM` | decision-time forecast per half-hour, actuals, 90% band, summary |
| `GET /api/accuracy?cutoff=HH:MM&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` | metrics, by forecast age, by hour, by day, error histogram; date filters are optional |
| `GET /api/health` | liveness |

## Key design decisions and assumptions

- **No hindsight.** For every target half-hour only forecasts with `publishTime <= cutoff` on the previous London day are eligible; the latest of those is used. This applies to the accuracy statistics too, so they describe what a buyer would really have seen.
- **Cutoff is an assumption.** The default is 09:30 London time on D-1 and is adjustable in the UI. Confirm the real gate time with the client.
- **Error sign.** `error = forecast - actual`. Positive means the forecast was too high (risk of under-buying other power).
- **Uncertainty band.** Empirical 5th to 95th percentile of `actual - forecast`, using only delivery days up to D-2 (day D-1 is still in progress at the cutoff). With fewer than 3 such days it falls back to the whole period and says so.
- **Cache instead of live calls.** Data is fetched once into CSVs, so the app is fast and keeps working if Elexon is down.
- **Time.** All data is UTC internally; day boundaries and labels use Europe/London.
- **Demand what-if.** Demand data is out of scope, so the app lets the user enter a flat demand figure and subtracts wind.

## Known limitations

- National level only; no regional breakdown, demand, or price data.
- The uncertainty band is a single national error distribution; in reality error size depends on the wind level and weather regime.
- Percentage errors (MAPE) are unstable when wind is near zero, so MW-based metrics are emphasised.
