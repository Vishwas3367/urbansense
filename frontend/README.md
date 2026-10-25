# UrbanSense frontend

React/Vite dashboard for the UrbanSense FastAPI/PostGIS sensor prototype.
The interface includes dashboard summaries, a live monitoring map, mobile
units, infrastructure issues, maintenance priority, analytics, search,
notifications, profile controls, and settings.

## Run locally

Start the backend first using [the backend setup guide](../backend/README.md).
Then run:

```bash
cd frontend
npm install
npm run dev
```

Sign in with `DASHBOARD_EMAIL` and `DASHBOARD_PASSWORD` from `backend/.env`.
The frontend makes authenticated API requests using the session token.

For local development, Vite proxies `/api` to `http://127.0.0.1:8000`. To use
a backend at another address, set `VITE_API_PROXY_TARGET` in `frontend/.env`.
For a deployed frontend where the API is on another origin, set
`VITE_API_BASE_URL` accordingly.

## Live data and display behavior

- Dashboard, monitoring, issues, mobile units, and maintenance pages are
  connected to authenticated backend endpoints.
- Analytics charts are computed from backend event and issue records and show
  empty states when there is no live data; they do not use fabricated sensor
  readings.
- Monitoring shows the latest vehicle temperature and humidity, sensor
  decisions, manual button signals, temperature alerts, potential impact
  classification, and motion-classifier confidence when available.
- Notifications distinguish high-temperature, manual-signal, potential
  impact, potential-pothole, and accepted sensor-decision records. A
  potential/manual signal is not the same as an accepted road issue.
- Settings and notifications are rendered above the map layer so the map
  cannot cover their overlays.
- Coverage-route visuals are still simulated demonstration content and should
  not be treated as actual device GPS coverage.

The displayed motion-classifier confidence is separate from the backend trust
confidence and final decision. Prototype sensor classifications and priority
scores are not validated operational measurements.

## Stack and structure

- React with JavaScript/JSX, Vite, Tailwind CSS, and React Router
- Recharts for analytics
- React Leaflet and OpenStreetMap tiles for maps
- Lucide icons
- `src/app/services`: authenticated API client
- `src/app/pages`: dashboard, monitoring, units, issues, maintenance,
  analytics, coverage, and login pages
- `src/app/components`: layout, map, cards, and shared UI
- `src/app/data`: remaining demonstration data, including simulated coverage

## Validate

```bash
npm run build
```
