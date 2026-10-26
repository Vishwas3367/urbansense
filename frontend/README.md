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
- Infrastructure Intelligence polls accepted issues and manual reports every
  10 seconds. Manual reports are shown separately with their backend-derived
  status (`PENDING`, `DEFERRED`, `REJECTED`, or `CONFIRMED`), decision, reasons,
  coordinates, vehicle, timestamp, and confidence. The accepted-issues table
  contains issues returned by the backend issue API; the dashboard does not
  promote a pending report into a confirmed issue itself.
- Live Monitoring polls vehicles, events, issues, and manual reports every
  10 seconds. The map uses backend GPS coordinates for reported manual
  candidates and distinct marker styles for pending, deferred, rejected, and
  confirmed statuses. Markers and tables reflect the latest fetched backend
  state; this prototype uses polling rather than a push connection.
- Mobile Units displays the latest backend temperature in its existing device
  details modal, in °C. Temperature and humidity are independently selected
  from fresh, non-null backend measurements; a missing or stale value is shown
  as unavailable rather than fabricated.
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

## API and prototype behavior

The API client in `src/app/services/api.js` attaches the dashboard bearer token
to authenticated requests. Backend authentication, input validation,
decisions, issue fusion, and persistence remain authoritative; the UI only
renders returned data. A reading's motion-classifier confidence is distinct
from its trust confidence and decision. HTTP success means ingestion completed,
not that a road issue was accepted.

Manual reports are fetched through the authenticated `/api/manual-reports`
endpoint. Their display status is derived from the saved backend decision.
Accepted issues come from `/api/issues`; map markers use actual returned GPS
coordinates. The 10-second refresh interval is best-effort polling, not a
real-time delivery guarantee.

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
