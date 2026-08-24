import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import { X, AlertTriangle } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default Leaflet marker icons in React apps
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const DISTRICT_LOCATIONS = [
  { id: 1, name: 'Coimbatore', lat: 11.0168, lng: 76.9558, temp: '29°C', rain: '85%', status: 'Heavy Rain Warning', alert: true },
  { id: 2, name: 'Chennai', lat: 13.0827, lng: 80.2707, temp: '33°C', rain: '30%', status: 'Light Rain', alert: false },
  { id: 3, name: 'New Delhi', lat: 28.6139, lng: 77.2090, temp: '34°C', rain: '10%', status: 'Clear Sky', alert: false },
  { id: 4, name: 'Nagapattinam', lat: 10.7672, lng: 79.8449, temp: '28°C', rain: '95%', status: 'Coastal Cyclone Alert', alert: true },
];

// Helper to invalidate Leaflet map size on modal open
function MapResizer() {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => {
      map.invalidateSize();
    }, 200);
  }, [map]);
  return null;
}

export default function MapModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="map-modal-overlay" onClick={onClose}>
      <div className="map-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="map-modal-header">
          <div className="map-title-box">
            <h3>IMD District Weather & Disaster Radar Map</h3>
            <span className="map-badge">Live Spatial Stream</span>
          </div>
          <button className="btn-close-map" onClick={onClose} aria-label="Close Map">
            <X size={20} />
          </button>
        </div>

        <div className="map-container-wrapper">
          <MapContainer 
            center={[11.0168, 76.9558]} 
            zoom={7} 
            scrollWheelZoom={true} 
            style={{ height: '420px', width: '100%', borderRadius: '12px' }}
          >
            <MapResizer />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {DISTRICT_LOCATIONS.map((loc) => (
              <React.Fragment key={loc.id}>
                <Marker position={[loc.lat, loc.lng]}>
                  <Popup>
                    <div className="map-popup-card">
                      <h4>{loc.name}</h4>
                      <p><strong>Temp:</strong> {loc.temp}</p>
                      <p><strong>Rainfall Prob:</strong> {loc.rain}</p>
                      <p className={`popup-status ${loc.alert ? 'alert' : ''}`}>
                        {loc.alert && <AlertTriangle size={14} />} {loc.status}
                      </p>
                    </div>
                  </Popup>
                </Marker>

                {loc.alert && (
                  <Circle 
                    center={[loc.lat, loc.lng]} 
                    radius={45000} 
                    pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.25 }} 
                  />
                )}
              </React.Fragment>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
