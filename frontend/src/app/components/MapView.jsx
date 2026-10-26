import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';

export default function MapView({ issues = [], vehicles = [], manualReports = [] }) {
  return (
    <MapContainer
      center={[12.9716, 79.1594]}
      zoom={13}
      scrollWheelZoom
      className="h-full w-full overflow-hidden"
    >
      <TileLayer
        attribution='&copy; OpenStreetMap'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {vehicles.filter((vehicle) => vehicle.lat !== 0 || vehicle.lng !== 0).map((v) => (
        <CircleMarker
          key={v.id}
          center={[v.lat, v.lng]}
          radius={8}
          pathOptions={{
            color: v.status === 'Offline' ? '#64748b' : '#22d3ee',
            fillColor: v.status === 'Offline' ? '#64748b' : '#22d3ee',
            fillOpacity: 0.9,
          }}
        >
          <Popup>
            <b>{v.id}</b>
            <br />
            Status: {v.status}
            <br />
            Speed: {v.speed} km/h
            <br />
            Sensors: {v.sensors}
          </Popup>
        </CircleMarker>
      ))}

      {issues.map((i) => (
        <CircleMarker
          key={i.id}
          center={[i.lat, i.lng]}
          radius={9}
          pathOptions={{
            color:
              i.severity === 'CRITICAL'
                ? '#ef4444'
                : i.severity === 'HIGH'
                  ? '#f97316'
                  : '#f59e0b',
            fillColor:
              i.severity === 'CRITICAL'
                ? '#ef4444'
                : i.severity === 'HIGH'
                  ? '#f97316'
                  : '#f59e0b',
            fillOpacity: 0.8,
          }}
        >
          <Popup>
            <b>{i.type}</b>
            <br />
            {i.location}
            <br />
            Confidence: {i.confidence}%
          </Popup>
        </CircleMarker>
      ))}

      {manualReports.map((report) => {
        const marker = {
          CONFIRMED: { color: '#16a34a', radius: 11, dashArray: undefined, fillOpacity: 0.9 },
          PENDING: { color: '#eab308', radius: 10, dashArray: '4 4', fillOpacity: 0.45 },
          DEFERRED: { color: '#f97316', radius: 10, dashArray: '4 4', fillOpacity: 0.45 },
          REJECTED: { color: '#ef4444', radius: 9, dashArray: '2 4', fillOpacity: 0.35 },
        }[report.detection_status] ?? {
          color: '#eab308',
          radius: 10,
          dashArray: '4 4',
          fillOpacity: 0.45,
        };
        return (
          <CircleMarker
            key={`manual-${report.event_id}`}
            center={[report.latitude, report.longitude]}
            radius={marker.radius}
            pathOptions={{
              color: marker.color,
              fillColor: marker.color,
              fillOpacity: marker.fillOpacity,
              dashArray: marker.dashArray,
              weight: 3,
            }}
          >
            <Popup>
              <b>Manual pothole report · {report.detection_status}</b>
              <br />
              Vehicle: {report.vehicle_id}
              <br />
              GPS: {report.latitude.toFixed(5)}, {report.longitude.toFixed(5)}
              <br />
              Decision: {report.decision} · Confidence: {report.confidence}%
              <br />
              {report.reasons.join(' ')}
            </Popup>
          </CircleMarker>
        );
      })}

      <Polyline
        positions={vehicles.slice(0, 4).map((v) => [v.lat, v.lng])}
        pathOptions={{
          color: '#22d3ee',
          weight: 2,
          opacity: 0.35,
          dashArray: '5 8',
        }}
      />
    </MapContainer>
  );
}
