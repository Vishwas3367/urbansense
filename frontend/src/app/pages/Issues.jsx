import { useEffect, useState } from 'react';
import { CheckCircle2, Users } from 'lucide-react';
import { Badge, severityTone } from '../components/Badge';
import Page, { Card } from '../components/Page';
import api from '../services/api';

export default function Issues() {
  const [issues, setIssues] = useState([]);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getIssues().then(setIssues).catch((requestError) => setError(requestError.message));
  }, []);

  return (
    <Page
      title="Infrastructure Intelligence"
      subtitle="Detected abnormalities verified through distributed mobile sensing."
    >
      {error && <Card className="mb-4 p-4 text-sm text-red-700">{error}</Card>}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-slate-600">
              <tr>
                {['Issue', 'Location', 'Type', 'Severity', 'Confidence', 'Detections', 'Status'].map((header) => (
                  <th key={header} className="px-5 py-4">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-white/5">
              {issues.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-5 py-8 text-center text-slate-500">
                    {error ? 'Could not load backend issues.' : 'No accepted anomalies have been recorded yet.'}
                  </td>
                </tr>
              )}
              {issues.map((issue) => (
                <tr
                  key={issue.id}
                  onClick={() => setSelectedIssue(issue)}
                  className="cursor-pointer hover:bg-white/[.025]"
                >
                  <td className="px-5 py-4">
                    <div className="font-semibold">{issue.id}</div>
                    <div className="text-xs text-slate-500">{issue.title}</div>
                  </td>
                  <td className="px-5 py-4 text-slate-400">{issue.location}</td>
                  <td className="px-5 py-4 text-slate-400">{issue.type}</td>
                  <td className="px-5 py-4">
                    <Badge tone={severityTone(issue.severity)}>{issue.severity}</Badge>
                  </td>
                  <td className="px-5 py-4 font-semibold">{issue.confidence}%</td>
                  <td className="px-5 py-4">{issue.detections} observations</td>
                  <td className="px-5 py-4 text-slate-400">{issue.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {selectedIssue && (
        <div
          onClick={() => setSelectedIssue(null)}
          className="fixed inset-0 z-50 grid place-items-center overflow-auto bg-black/70 p-4"
        >
          <div
            onClick={(event) => event.stopPropagation()}
            className="w-full max-w-3xl rounded-2xl border border-white/10 bg-[#0b1827] p-6"
          >
            <div className="flex flex-col justify-between gap-3 sm:flex-row">
              <div>
                <div className="text-xs text-cyan-300">{selectedIssue.id}</div>
                <h2 className="mt-1 text-2xl font-bold">{selectedIssue.title}</h2>
                <p className="mt-1 text-xs text-slate-500">
                  {selectedIssue.location} · {selectedIssue.time}
                </p>
              </div>
              <Badge tone={severityTone(selectedIssue.severity)}>{selectedIssue.severity}</Badge>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl bg-white/[.03] p-4">
                <div className="text-xs text-slate-500">Confidence</div>
                <div className="mt-1 text-2xl font-bold">{selectedIssue.confidence}%</div>
              </div>
              <div className="rounded-xl bg-white/[.03] p-4">
                <div className="text-xs text-slate-500">Detections</div>
                <div className="mt-1 text-2xl font-bold">{selectedIssue.detections}</div>
              </div>
              <div className="rounded-xl bg-white/[.03] p-4">
                <div className="text-xs text-slate-500">Peak Vibration</div>
                <div className="mt-1 text-2xl font-bold">{selectedIssue.vibration} g</div>
              </div>
            </div>

            <div className="mt-5 rounded-xl border border-cyan-400/10 bg-cyan-400/5 p-5">
              <div className="flex items-center gap-2 font-semibold">
                <Users size={18} className="text-cyan-300" />
                Contributing Sensing Units
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                This issue combines accepted observations from the listed mobile sensing units.
                Independent nearby vehicles contribute corroboration to the event confidence.
              </p>

              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {selectedIssue.vehicles.map((vehicle) => (
                  <div
                    key={vehicle}
                    className="flex items-center gap-2 rounded-lg border border-white/10 p-3 text-xs"
                  >
                    <CheckCircle2 size={15} className="text-emerald-300" />
                    {vehicle}
                    <span className="ml-auto text-emerald-300">confirmed</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <button className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950">
                View Location
              </button>
              <button className="rounded-xl border border-white/10 px-4 py-2 text-sm">
                Create Maintenance Task
              </button>
            </div>
          </div>
        </div>
      )}
    </Page>
  );
}
