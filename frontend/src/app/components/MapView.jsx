import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';

export default function MapView({ issues = [], vehicles = [] }) {
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
