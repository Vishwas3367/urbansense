import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Page, { Card } from '../components/Page';
import api from '../services/api';

const severityColors = ['#ef4444', '#f97316', '#f59e0b', '#22c55e'];
const severityLevels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function buildAnalytics(events, issues) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setDate(today.getDate() - 6 + index);
    return {
      key: dateKey(date),
      day: date.toLocaleDateString(undefined, { weekday: 'short' }),
      readings: 0,
    };
  });
  const dayByKey = new Map(days.map((day) => [day.key, day]));
  const vehicleCounts = new Map();

  events.forEach((event) => {
    const receivedAt = new Date(event.received_at);
    if (!Number.isNaN(receivedAt.getTime())) {
      const day = dayByKey.get(dateKey(receivedAt));
      if (day) day.readings += 1;
    }
    vehicleCounts.set(event.vehicle_id, (vehicleCounts.get(event.vehicle_id) ?? 0) + 1);
  });

  const issueTypeCounts = new Map();
  issues.forEach((issue) => {
    issueTypeCounts.set(issue.type, (issueTypeCounts.get(issue.type) ?? 0) + 1);
  });

  const severityCounts = severityLevels.map((level) => ({
    name: level.charAt(0) + level.slice(1).toLowerCase(),
    value: issues.filter((issue) => issue.severity === level).length,
  }));

  const vehicles = [...vehicleCounts.entries()]
    .map(([id, readings]) => ({ id, readings }))
    .sort((a, b) => b.readings - a.readings)
    .slice(0, 8);

  return {
    trend: days.map(({ day, readings }) => ({ day, readings })),
    types: [...issueTypeCounts.entries()]
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value),
    severity: severityCounts,
    vehicles,
  };
}

function EmptyChart({ message }) {
  return (
    <div className="grid h-full place-items-center text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

export default function Analytics() {
  const [events, setEvents] = useState([]);
  const [issues, setIssues] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      try {
        const [nextEvents, nextIssues] = await Promise.all([
          api.getEvents(),
          api.getIssues(),
        ]);
        if (!isMounted) return;
        setEvents(nextEvents);
        setIssues(nextIssues);
        setError('');
      } catch (requestError) {
        if (isMounted) setError(requestError.message);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    load();
    const interval = setInterval(load, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const analytics = useMemo(() => buildAnalytics(events, issues), [events, issues]);
  const hasIssues = issues.length > 0;
  const hasEvents = events.length > 0;

  return (
    <Page
      title="Urban Infrastructure Analytics"
      subtitle="Analytics from backend records. Readings charts use the latest 50 sensor events."
    >
      {error && (
        <Card className="mb-4 border-red-200 p-4 text-sm text-red-700">
          Unable to load live analytics: {error}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="font-semibold">Recent Readings by Day</h2>
          <div className="mt-5 h-72">
            {isLoading ? (
              <EmptyChart message="Loading sensor readings…" />
            ) : !hasEvents ? (
              <EmptyChart message="No sensor readings have been received yet." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={analytics.trend}>
                  <XAxis dataKey="day" stroke="#64748b" />
                  <YAxis allowDecimals={false} stroke="#64748b" />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1827',
                      border: '1px solid #233246',
                      borderRadius: 12,
                    }}
                  />
                  <Line type="monotone" dataKey="readings" stroke="#22d3ee" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold">Issues by Type</h2>
          <div className="mt-5 h-72">
            {isLoading ? (
              <EmptyChart message="Loading issues…" />
            ) : !hasIssues ? (
              <EmptyChart message="No infrastructure issues have been recorded." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.types}>
                  <XAxis dataKey="name" stroke="#64748b" />
                  <YAxis allowDecimals={false} stroke="#64748b" />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1827',
                      border: '1px solid #233246',
                      borderRadius: 12,
                    }}
                  />
                  <Bar dataKey="value" fill="#22d3ee" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold">Severity Distribution</h2>
          <div className="mt-5 h-72">
            {isLoading ? (
              <EmptyChart message="Loading issues…" />
            ) : !hasIssues ? (
              <EmptyChart message="No issue severity data is available." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analytics.severity}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={95}
                    innerRadius={58}
                  >
                    {analytics.severity.map((_, index) => (
                      <Cell key={index} fill={severityColors[index]} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1827',
                      border: '1px solid #233246',
                      borderRadius: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold">Recent Readings by Vehicle</h2>
          <div className="mt-5 h-72">
            {isLoading ? (
              <EmptyChart message="Loading sensor readings…" />
            ) : !hasEvents ? (
              <EmptyChart message="No vehicle readings have been received yet." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.vehicles}>
                  <XAxis dataKey="id" stroke="#64748b" />
                  <YAxis allowDecimals={false} stroke="#64748b" />
                  <Tooltip
                    contentStyle={{
                      background: '#0b1827',
                      border: '1px solid #233246',
                      borderRadius: 12,
                    }}
                  />
                  <Bar dataKey="readings" fill="#60a5fa" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Card>
      </div>

      <Card className="mt-4 p-5">
        <h2 className="font-semibold">Vehicle Contribution</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {analytics.vehicles.map((vehicle) => (
            <div key={vehicle.id} className="rounded-xl border border-white/10 p-4">
              <div className="text-sm font-semibold">{vehicle.id}</div>
              <div className="mt-2 text-2xl font-bold">{vehicle.readings}</div>
              <div className="text-xs text-slate-500">readings in latest 50 events</div>
            </div>
          ))}
          {!isLoading && !hasEvents && (
            <p className="text-sm text-slate-500">
              No vehicle contribution data is available until sensors send readings.
            </p>
          )}
        </div>
      </Card>
    </Page>
  );
}
