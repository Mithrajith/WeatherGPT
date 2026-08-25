import React, { useEffect, useState, useCallback } from 'react';
import { Thermometer, Droplets, Wind, Gauge, RefreshCw, MapPin, Search } from 'lucide-react';
import { fetchCurrentWeather, fetchForecast } from '../services/api';

const DEFAULT_LOCATION = 'Coimbatore';

function StatTile({ icon, label, value, unit }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile-icon">{icon}</div>
      <div className="stat-tile-body">
        <span className="stat-tile-label">{label}</span>
        <span className="stat-tile-value">
          {value ?? '—'}
          {value != null && unit ? <span className="stat-tile-unit">{unit}</span> : null}
        </span>
      </div>
    </div>
  );
}

function ForecastDayCard({ day }) {
  const date = day.date ? new Date(day.date) : null;
  return (
    <div className="forecast-day-card">
      <span className="forecast-day-label">
        {date ? date.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' }) : '—'}
      </span>
      <span className="forecast-day-condition">{day.condition || '—'}</span>
      <span className="forecast-day-temps">
        <strong>{day.temp_max != null ? Math.round(day.temp_max) : '—'}°</strong>
        <span className="forecast-day-min">{day.temp_min != null ? Math.round(day.temp_min) : '—'}°</span>
      </span>
      {day.rain_chance != null && (
        <span className="forecast-day-rain">{day.rain_chance}% rain</span>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [location, setLocation] = useState(DEFAULT_LOCATION);
  const [locationInput, setLocationInput] = useState(DEFAULT_LOCATION);
  const [current, setCurrent] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [source, setSource] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async (place) => {
    setIsLoading(true);
    setError(null);
    try {
      const [currentData, forecastData] = await Promise.all([
        fetchCurrentWeather(place),
        fetchForecast(place, 5),
      ]);
      setCurrent(currentData.current || null);
      setSource(currentData.source || null);
      setForecast(forecastData.forecast || []);
    } catch (err) {
      setError(err.message);
      setCurrent(null);
      setForecast([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load(location);
  }, [location, load]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (locationInput.trim()) setLocation(locationInput.trim());
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <h2>Live Weather Dashboard</h2>
          <span className="dashboard-subtitle">
            <MapPin size={13} /> {location}
          </span>
        </div>

        <form className="dashboard-search" onSubmit={handleSearch}>
          <Search size={14} />
          <input
            type="text"
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            placeholder="Search a district or city…"
          />
        </form>

        <button className="refresh-btn" onClick={() => load(location)} title="Refresh">
          <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
        </button>
      </div>

      {error && <p className="alerts-error-note">Couldn't load live data: {error}</p>}

      <div className="stat-tile-grid">
        <StatTile icon={<Thermometer size={18} />} label="Temperature" value={current?.temperature != null ? Math.round(current.temperature) : null} unit="°C" />
        <StatTile icon={<Droplets size={18} />} label="Humidity" value={current?.humidity} unit="%" />
        <StatTile icon={<Gauge size={18} />} label="Rainfall" value={current?.precipitation} unit="mm" />
        <StatTile icon={<Wind size={18} />} label="Wind" value={current?.wind_speed} unit="km/h" />
      </div>

      {current?.condition && (
        <div className="dashboard-condition-banner">
          <span>{current.condition}</span>
          {source && <span className="dashboard-source">{source}</span>}
        </div>
      )}

      <h3 className="dashboard-section-title">5-Day Forecast</h3>
      <div className="forecast-day-list">
        {forecast.length === 0 && !isLoading && (
          <div className="alerts-empty">No forecast data available right now.</div>
        )}
        {forecast.map((day, i) => (
          <ForecastDayCard key={day.date || i} day={day} />
        ))}
      </div>
    </div>
  );
}
