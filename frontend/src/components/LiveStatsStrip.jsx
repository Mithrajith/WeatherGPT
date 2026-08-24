import React from 'react';
import { Thermometer, Droplets, CloudRain, Wind } from 'lucide-react';

export default function LiveStatsStrip({ stats }) {
  if (!stats) return null;

  return (
    <div className="live-stats-strip">
      <div className="stat-item">
        <div className="stat-icon-wrapper temp">
          <Thermometer size={16} />
        </div>
        <div className="stat-text-group">
          <span className="stat-label">TEMP</span>
          <span className="stat-value">{stats.tempCurrent}°C</span>
          <span className="stat-sub">{stats.tempMax}° / {stats.tempMin}°</span>
        </div>
      </div>

      <div className="stat-item divider"></div>

      <div className="stat-item">
        <div className="stat-icon-wrapper rain">
          <CloudRain size={16} />
        </div>
        <div className="stat-text-group">
          <span className="stat-label">RAIN TODAY</span>
          <span className="stat-value">{stats.rainTodayMm} mm</span>
          <span className="stat-sub">Moderate</span>
        </div>
      </div>

      <div className="stat-item divider"></div>

      <div className="stat-item">
        <div className="stat-icon-wrapper humidity">
          <Droplets size={16} />
        </div>
        <div className="stat-text-group">
          <span className="stat-label">HUMIDITY</span>
          <span className="stat-value">{stats.humidity}%</span>
          <span className="stat-sub">High</span>
        </div>
      </div>

      <div className="stat-item divider"></div>

      <div className="stat-item">
        <div className="stat-icon-wrapper wind">
          <Wind size={16} />
        </div>
        <div className="stat-text-group">
          <span className="stat-label">WIND</span>
          <span className="stat-value">{stats.windSpeedKmh} <span className="unit">km/h</span></span>
          <span className="stat-sub">{stats.windDirection}</span>
        </div>
      </div>
    </div>
  );
}
