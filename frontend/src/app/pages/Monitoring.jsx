import { useEffect, useState } from 'react';
import { Activity, Clock } from 'lucide-react';
import { Badge } from '../components/Badge';
import MapView from '../components/MapView';
import Page, { Card } from '../components/Page';
import api from '../services/api';

export default function Monitoring() {
  const [vehicles, setVehicles] = useState([]);
  const [issues, setIssues] = useState([]);
  const [manualReports, setManualReports] = useState([]);
  const [events, setEvents] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const [nextVehicles, nextIssues, nextEvents, nextManualReports] = await Promise.all([
          api.getVehicles(),
          api.getIssues(),
          api.getEvents(),
          api.getManualReports(),
        ]);
        if (!isMounted) return;
        setVehicles(nextVehicles);
        setIssues(nextIssues);
        setEvents(nextEvents);
        setManualReports(nextManualReports);
        setSelectedVehicle((current) =>
          nextVehicles.find((vehicle) => vehicle.id === current?.id) ?? nextVehicles[0] ?? null
        );
        setError('');
      } catch (requestError) {
        if (isMounted) setError(requestError.message);
      }
    };
    load();
    const interval = setInterval(load, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <Page
      title="Live Urban Monitoring"
      subtitle="Live authenticated readings and anomaly-processing decisions from registered devices."
    >
      {error && <Card className="mb-4 p-4 text-sm text-red-700">{error}</Card>}
      <div className="grid gap-4 xl:grid-cols-[1.6fr_.7fr]">
        <Card className="overflow-hidden">
          <div className="flex justify-between border-b border-white/10 p-5">
            <div>
              <h2 className="font-semibold">Live Sensing Map</h2>
              <p className="mt-1 text-xs text-slate-500">Backend device telemetry</p>
            </div>
            <Badge tone={error ? 'red' : 'green'}>{error ? 'OFFLINE' : 'LIVE'}</Badge>
          </div>
          <div className="h-[520px]">
            <MapView issues={issues} vehicles={vehicles} manualReports={manualReports} />
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="p-5">
            <h2 className="font-semibold">Selected Mobile Node</h2>

            {selectedVehicle ? <div className="mt-4 rounded-xl border border-cyan-400/15 bg-cyan-400/5 p-4">
              <div className="flex justify-between">
                <div className="font-bold">{selectedVehicle.id}</div>
                <Badge tone="green">{selectedVehicle.status}</Badge>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                {[
                  ['Speed', `${selectedVehicle.speed} km/h`],
                  ['Zone', selectedVehicle.zone],
                  ['Trust', `${selectedVehicle.trust ?? 0}%`],
                  ['Location', `${selectedVehicle.lat}, ${selectedVehicle.lng}`],
                  ['Sensors', selectedVehicle.sensors],
                  ['Temperature', selectedVehicle.temperature_c == null ? 'No reading' : `${selectedVehicle.temperature_c} °C`],
                  ['Humidity', selectedVehicle.humidity_percent == null ? 'No reading' : `${selectedVehicle.humidity_percent}%`],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="text-slate-500">{label}</div>
                    <div className="mt-1 font-semibold">{value}</div>
                  </div>
                ))}
              </div>

              <div className="mt-4 rounded-lg border border-amber-400/10 bg-amber-400/5 p-3 text-xs">
                <div className="flex items-center gap-2 text-amber-300">
                  <Activity size={14} />
                  Trust-aware processing
                </div>
                <div className="mt-1 text-slate-500">
                  Readings are authenticated, validated, and compared with independent observations.
                </div>
              </div>
            </div> : (
              <p className="mt-4 rounded-xl border border-dashed border-white/10 p-4 text-sm text-slate-500">
                No registered devices are available yet.
              </p>
            )}

            <div className="mt-3 flex gap-2 overflow-x-auto">
              {vehicles.map((vehicle) => (
                <button
                  key={vehicle.id}
                  onClick={() => setSelectedVehicle(vehicle)}
                  className="whitespace-nowrap rounded-lg border border-white/10 px-3 py-2 text-xs hover:border-cyan-400/30"
                >
                  {vehicle.id}
                </button>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="font-semibold">Live Events</h2>
            <div className="mt-4 space-y-3">
              {events.map((event) => (
                <div key={event.event_id} className="flex gap-3">
                  <div className="mt-1 h-2 w-2 rounded-full bg-cyan-400" />
                  <div>
                    <div className="text-xs text-slate-300">
                      {event.vehicle_id} · {event.decision} · {event.confidence}% confidence
                    </div>
                    <div className="mt-1 text-[10px] text-slate-500">
                      {event.temperature_c == null ? 'Temperature unavailable' : `${event.temperature_c} °C`}
                      {' · '}
                      {event.humidity_percent == null ? 'Humidity unavailable' : `${event.humidity_percent}% humidity`}
                    </div>
                    {event.event_classification && (
                      <div className="mt-1 text-[10px] font-semibold text-cyan-400">
                        {event.event_classification.replaceAll('_', ' ')}
                        {event.pothole_confidence == null
                          ? ''
                          : ` · ${event.pothole_confidence}% motion confidence`}
                      </div>
                    )}
                    {event.manual_trigger && (
                      <div className="mt-1 text-[10px] font-semibold text-amber-400">
                        Manual pothole signal · detector decision remains {event.decision}
                      </div>
                    )}
                    {event.impact_detected && (
                      <div className="mt-1 text-[10px] font-semibold text-amber-400">
                        Potential road impact · {event.impact_peak_g?.toFixed(2) ?? '—'} g · {event.location}
                      </div>
                    )}
                    {event.temperature_alert && (
                      <div className="mt-1 text-[10px] font-semibold text-red-400">
                        High-temperature alert at this location
                      </div>
                    )}
                    <div className="mt-1 flex items-center gap-1 text-[10px] text-slate-600">
                      <Clock size={10} />
                      {new Date(event.received_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
              {events.length === 0 && (
                <p className="text-sm text-slate-500">No sensor readings have been received yet.</p>
              )}
            </div>
          </Card>
        </div>
      </div>
    </Page>
  );
}
