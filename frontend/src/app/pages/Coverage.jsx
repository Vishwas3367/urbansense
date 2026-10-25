import { Coins, MapPinned, Radio, Route } from 'lucide-react';
import { Badge } from '../components/Badge';
import MapView from '../components/MapView';
import Page, { Card } from '../components/Page';

function Mini({ icon: Icon, label, value }) {
  return (
    <Card className="p-4">
      <Icon size={17} className="text-cyan-300" />
      <div className="mt-3 text-xl font-bold">{value}</div>
      <div className="text-[11px] text-slate-500">{label}</div>
    </Card>
  );
}
export default function Coverage() {
  return (
    <Page
      title="Opportunistic City Coverage"
      subtitle="See how moving vehicles create large-scale sensing coverage without fixed sensors everywhere."
    >
      <div className="grid gap-4 lg:grid-cols-[1.5fr_.7fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-white/10 p-5">
            <h2 className="font-semibold">Vehicle Routes & Coverage</h2>
            <p className="mt-1 text-xs text-slate-500">
              Simulated routes demonstrate opportunistic sensing.
            </p>
          </div>
          <div className="h-[500px]">
            <MapView />
          </div>
        </Card>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Mini icon={Radio} label="Mobile nodes" value="24" />
            <Mini icon={Route} label="Road segments" value="1,284" />
            <Mini icon={MapPinned} label="City coverage" value="87%" />
            <Mini icon={Coins} label="Fixed sensors" value="0" />
          </div>

          <Card className="p-5">
            <Badge tone="blue">CORE CONCEPT</Badge>
            <h2 className="mt-4 text-xl font-bold">
              Monitor the city without instrumenting the entire city.
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              UrbanSense uses existing moving vehicles IoT sensing nodes. Infrastructure
              observations are collected opportunistically travel through different parts of the city.
            </p>

            <div className="mt-5 space-y-3">
              {[
                'Existing vehicles become sensing nodes',
                'Data is collected naturally overlap',
                'Repeated observations improve confidence',
                'Only high-risk locations require targeted inspection',
              ].map((item, index) => (
                <div key={item} className="flex gap-3 text-xs text-slate-400">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-cyan-400/10 text-cyan-300">
                    {index + 1}
                  </span>
                  {item}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </Page>
  );
}
