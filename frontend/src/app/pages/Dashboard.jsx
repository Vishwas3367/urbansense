import { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  MapPinned,
  Truck,
} from 'lucide-react';
import { Badge, severityTone } from '../components/Badge';
import MapView from '../components/MapView';
import Page, { Card } from '../components/Page';
import StatCard from '../components/StatCard';
import api from '../services/api';

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [issues, setIssues] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api.getSummary(),
      api.getVehicles(),
      api.getIssues(),
      api.getAlerts(),
    ])
      .then(([nextSummary, nextVehicles, nextIssues, nextAlerts]) => {
        setSummary(nextSummary);
        setVehicles(nextVehicles);
        setIssues(nextIssues);
        setAlerts(nextAlerts);
      })
      .catch((requestError) => setError(requestError.message));
  }, []);

  const trust = summary?.average_sensor_trust ?? 0;
  const healthMetrics = [
    ['Sensor trust', summary?.average_sensor_trust ?? 0],
    ['Reading quality', summary?.average_reading_quality ?? 0],
    ['Accepted readings', summary?.accepted_readings_pct ?? 0],
  ];

  return (
    <Page
      title="Urban Infrastructure Overview"
      subtitle="Real-time intelligence from mobile IoT sensing nodes across the city."
    >
      {error && (
        <Card className="mb-4 border-red-200 p-4 text-sm text-red-700">
          Unable to load live backend data: {error}
        </Card>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Active Mobile Units" value={summary?.active_units ?? '—'} trend={`${summary?.registered_units ?? 0} registered`} icon={Truck} />
        <StatCard label="GPS Grid Cells Observed" value={summary?.segments_covered ?? '—'} trend="last 24 hours" icon={MapPinned} />
        <StatCard label="Infrastructure Issues" value={summary?.issues ?? '—'} trend={`${summary?.new_issues ?? 0} recent`} icon={AlertTriangle} />
        <StatCard label="Critical Issues" value={summary?.critical_issues ?? '—'} trend={summary?.critical_issues ? 'Attention' : 'No critical issues'} icon={Activity} />
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1.7fr_.7fr]">
        <Card className="overflow-hidden">
          <div className="smart-divider flex items-center justify-between border-b border-white/10 p-4">
            <div>
              <h2 className="font-semibold">Live Urban Coverage</h2>
              <p className="mt-1 text-xs text-slate-500">
                Latest authenticated vehicle readings and accepted road issues
              </p>
            </div>
            <Badge tone="green">{vehicles.filter((vehicle) => vehicle.status === 'Active').length} active nodes</Badge>
          </div>
          <div className="h-[300px]">
            <MapView issues={issues} vehicles={vehicles} />
          </div>
        </Card>

        <Card className="p-4">
          <h2 className="font-semibold">Infrastructure Health</h2>
          <p className="mt-1 text-xs text-slate-500">Measured from registered sensor data</p>

          <div
            className="mx-auto my-5 grid h-32 w-32 place-items-center rounded-full p-2"
            style={{ background: `conic-gradient(#06b6d4 0 ${trust}%, #d8f2f6 ${trust}% 100%)` }}
          >
            <div className="grid h-full w-full place-items-center rounded-full bg-white">
              <div className="text-center">
                <div className="text-3xl font-bold">{trust}%</div>
                <div className="text-[10px] text-emerald-300">Sensor trust</div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {healthMetrics.map(([title, value]) => (
              <div key={title}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="text-slate-400">{title}</span>
                  <span>{value}%</span>
                </div>
                <div className="smart-progress-bg h-1.5 rounded-full bg-white/5">
                  <div className="smart-progress h-full rounded-full bg-cyan-400" style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="mt-3">
        <div className="smart-divider border-b border-white/10 p-4">
          <h2 className="font-semibold">Recent Sensor Decisions</h2>
        </div>

        <div className="divide-y divide-white/5">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="font-medium text-sm">{alert.title}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {alert.location} · {alert.time}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Badge
                  tone={
                    alert.alert_type === 'HIGH_TEMPERATURE'
                      ? 'red'
                      : alert.alert_type === 'POTENTIAL_IMPACT'
                        ? 'amber'
                        : severityTone(alert.severity)
                  }
                >
                  {alert.alert_type === 'HIGH_TEMPERATURE'
                    ? 'HIGH TEMPERATURE'
                    : alert.alert_type === 'MANUAL_SIGNAL'
                      ? `MANUAL · ${alert.decision}`
                      : alert.alert_type === 'POTENTIAL_POTHOLE'
                        ? 'POTENTIAL POTHOLE'
                        : alert.alert_type === 'POTENTIAL_IMPACT'
                        ? 'POTENTIAL IMPACT'
                        : alert.decision}
                </Badge>
                {alert.alert_type === 'HIGH_TEMPERATURE' ? (
                  <span className="text-xs text-slate-400">
                    {alert.temperature_c} °C · {alert.humidity_percent ?? '—'}% humidity
                  </span>
                ) : alert.alert_type === 'POTENTIAL_IMPACT' ? (
                  <span className="text-xs text-slate-400">
                    {alert.impact_peak_g?.toFixed(2) ?? '—'} g · detector decision: {alert.decision}
                  </span>
                ) : alert.alert_type === 'POTENTIAL_POTHOLE' ? (
                  <span className="text-xs text-slate-400">
                    {alert.pothole_confidence ?? '—'}% motion confidence · {alert.decision}
                  </span>
                ) : (
                  <span className="text-xs text-slate-400">{alert.confidence}% confidence</span>
                )}
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <p className="p-4 text-sm text-slate-500">
              {summary ? 'No sensor alerts have been recorded yet.' : 'Loading sensor events…'}
            </p>
          )}
        </div>
      </Card>
    </Page>
  );
}
