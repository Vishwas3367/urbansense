import { useEffect, useState } from 'react';
import Page, { Card } from '../components/Page';
import { Badge, severityTone } from '../components/Badge';
import { ShieldAlert, Wrench } from 'lucide-react';
import api from '../services/api';

const groups = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

const riskDetails = {
  CRITICAL: {
    iconColor: 'text-red-300',
  },
  HIGH: {
    iconColor: 'text-orange-300',
  },
  MEDIUM: {
    iconColor: 'text-amber-300',
  },
  LOW: {
    iconColor: 'text-slate-300',
  },
};

export default function Maintenance() {
  const [issues, setIssues] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getMaintenance().then(setIssues).catch((requestError) => setError(requestError.message));
  }, []);

  return (
    <Page
      title="Predictive Maintenance Priority"
      subtitle="Prioritize accepted sensor events using their calculated severity and confidence."
    >
      {error && <Card className="mb-4 p-4 text-sm text-red-700">{error}</Card>}
      <div className="grid gap-4 lg:grid-cols-3">
        {groups.map((group) => {
          const details = riskDetails[group];
          const groupIssues = issues.filter((issue) => issue.severity === group);

          return (
            <Card key={group} className="p-5">
              <div className="flex items-center justify-between">
                <div className="font-semibold">{group}</div>
                <Badge tone={severityTone(group)}>{groupIssues.length} issues</Badge>
              </div>

              <div className="mt-5 space-y-3">
                {groupIssues.map((issue) => (
                  <div
                    key={issue.id}
                    className="rounded-xl border border-white/10 bg-white/[.02] p-4"
                  >
                    <div className="flex justify-between gap-3">
                      <div className="text-sm font-semibold">{issue.location}</div>
                      <ShieldAlert size={16} className={details.iconColor} />
                    </div>

                    <div className="mt-1 text-xs text-slate-500">{issue.title}</div>

                    <div className="mt-4 flex items-end justify-between">
                      <div>
                        <div className="text-xs text-slate-500">Priority Score</div>
                        <div className="text-2xl font-bold">
                              {issue.priorityScore}
                          <span className="text-sm text-slate-600">/100</span>
                        </div>
                      </div>

                      <div className="text-right text-xs text-slate-500">
                        Risk · Confidence
                        <br />
                        <span className="font-semibold text-slate-300">
                          {issue.riskScore} · {issue.confidence}%
                        </span>
                      </div>
                    </div>

                    <div className="mt-4 text-xs text-slate-400">
                      <Wrench size={13} className="mr-1 inline" />
                      {issue.recommendedAction}
                    </div>
                  </div>
                ))}

                {groupIssues.length === 0 && (
                  <div className="rounded-xl border border-dashed border-white/10 p-4 text-center text-sm text-slate-500">
                    No {group.toLowerCase()} priority issues.
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <Card className="mt-4 p-6">
        <h2 className="font-semibold">Prototype Priority Model</h2>
        <p className="mt-1 text-xs text-slate-500">
          A transparent prototype score for demonstration; it is not a validated
          municipal maintenance model.
        </p>

        <div className="mt-5 grid gap-3 md:grid-cols-5">
          {[
            ['Severity', '55%'],
            ['Confidence', '30%'],
            ['Repeated detections', '15%'],
          ].map(([item, weight], index) => (
            <div
              key={item}
              className="rounded-xl border border-white/10 p-4 text-center"
            >
              <div className="mx-auto mb-2 grid h-9 w-9 place-items-center rounded-lg bg-cyan-400/10 text-cyan-300">
                {index + 1}
              </div>
              <div className="text-xs font-medium">{item}</div>
              <div className="mt-1 text-[10px] text-slate-500">{weight} weight</div>
              {index < 4 && <div className="mt-3 text-slate-600">+</div>}
            </div>
          ))}
        </div>
      </Card>
    </Page>
  );
}
