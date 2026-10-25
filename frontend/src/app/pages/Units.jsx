import { useEffect, useState } from 'react';
import { MapPin, Search } from 'lucide-react';
import { Badge } from '../components/Badge';
import Page, { Card } from '../components/Page';
import api from '../services/api';

export default function Units() {
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.getVehicles().then(setVehicles).catch((requestError) => setError(requestError.message));
  }, []);

  const filteredVehicles = vehicles.filter((vehicle) =>
    `${vehicle.id} ${vehicle.zone} ${vehicle.type}`.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <Page title="Mobile IoT Sensing Units" subtitle="Existing city vehicles acting mobile sensing nodes.">
      {error && <Card className="mb-4 p-4 text-sm text-red-700">{error}</Card>}
      <Card>
        <div className="flex flex-col gap-3 border-b border-white/10 p-4 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 text-slate-600" size={16} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search vehicle, zone or type..."
              className="w-full rounded-xl border border-white/10 bg-white/[.03] py-2 pl-9 text-sm outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-white/[.02] text-xs uppercase tracking-wider text-slate-600">
              <tr>
                {['Vehicle', 'Type', 'Status', 'Zone', 'Speed', 'Sensors', 'Last Update'].map((header) => (
                  <th key={header} className="px-5 py-4">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-white/5">
              {filteredVehicles.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-5 py-8 text-center text-slate-500">
                    {error ? 'Could not load registered devices.' : 'No devices have been registered yet.'}
                  </td>
                </tr>
              )}
              {filteredVehicles.map((vehicle) => (
                <tr
                  key={vehicle.id}
                  onClick={() => setSelectedVehicle(vehicle)}
                  className="cursor-pointer hover:bg-white/[.025]"
                >
                  <td className="px-5 py-4 font-semibold">{vehicle.id}</td>
                  <td className="px-5 py-4 text-slate-400">{vehicle.type}</td>
                  <td className="px-5 py-4">
                    <Badge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Warning' ? 'yellow' : 'gray'}>
                      {vehicle.status}
                    </Badge>
                  </td>
                  <td className="px-5 py-4 text-slate-400">{vehicle.zone}</td>
                  <td className="px-5 py-4">{vehicle.speed} km/h</td>
                  <td className="px-5 py-4">{vehicle.sensors}</td>
                  <td className="px-5 py-4 text-slate-500">
                    {vehicle.status === 'Active' ? 'Recently received' : 'No recent reading'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {selectedVehicle && (
        <div onClick={() => setSelectedVehicle(null)} className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
          <div onClick={(event) => event.stopPropagation()} className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#0b1827] p-6">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xl font-bold">{selectedVehicle.id}</div>
                <div className="text-xs text-slate-500">
                  {selectedVehicle.type} · {selectedVehicle.zone}
                </div>
              </div>
              <Badge tone={selectedVehicle.status === 'Active' ? 'green' : selectedVehicle.status === 'Warning' ? 'yellow' : 'gray'}>
                {selectedVehicle.status}
              </Badge>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              {[
                ['Speed', `${selectedVehicle.speed} km/h`],
                ['Distance', `${selectedVehicle.distance} km`],
                ['Segments', selectedVehicle.segments],
                ['Observations', selectedVehicle.observations],
                ['Anomalies', selectedVehicle.anomalies],
                ['Sensors', selectedVehicle.sensors],
                ['Trust', `${selectedVehicle.trust ?? 0}%`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-white/10 bg-white/[.025] p-4">
                  <div className="text-xs text-slate-500">{label}</div>
                  <div className="mt-1 font-bold">{value}</div>
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-xl bg-white/[.025] p-4 text-sm">
              <div className="flex items-center gap-2 text-cyan-300">
                <MapPin size={16} />
                {selectedVehicle.lat}, {selectedVehicle.lng}
              </div>
              <div className="mt-2 text-xs text-slate-500">
                Current GPS position · simulated prototype data
              </div>
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}
