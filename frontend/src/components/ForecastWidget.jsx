import React from 'react';
import { CloudRain, Sun, CloudLightning, Cloud, CloudDrizzle, ShieldCheck, AlertTriangle, AlertOctagon, Droplets } from 'lucide-react';

function getWeatherIcon(condition) {
  const cond = (condition || '').toLowerCase();
  if (cond.includes('thunder')) return <CloudLightning className="weather-icon storm" size={20} />;
  if (cond.includes('heavy') || cond.includes('downpour')) return <CloudRain className="weather-icon rain-heavy" size={20} />;
  if (cond.includes('light') || cond.includes('shower') || cond.includes('drizzle')) return <CloudDrizzle className="weather-icon drizzle" size={20} />;
  if (cond.includes('cloud')) return <Cloud className="weather-icon cloud" size={20} />;
  return <Sun className="weather-icon sun" size={20} />;
}

export default function ForecastWidget({ forecast }) {
  if (!forecast || forecast.length === 0) return null;

  return (
    <div className="forecast-section-clean">
      <div className="forecast-header-clean">
        <span className="forecast-title-clean">7-DAY IMD RAINFALL & RISK FORECAST</span>
        <span className="forecast-tag-clean">Live NWP Data</span>
      </div>

      <div className="forecast-row-clean">
        {forecast.map((item, idx) => {
          const severity = item.severity || (item.rainProb > 70 ? 'alert' : item.rainProb > 40 ? 'caution' : 'safe');
          
          return (
            <div key={idx} className={`forecast-col-item severity-${severity}`}>
              <span className="col-day-text">{item.day}</span>
              <div className="col-icon-box">{getWeatherIcon(item.condition)}</div>
              
              <div className="col-temp-group">
                <span className="t-high">{item.tempMax}°</span>
                <span className="t-low">{item.tempMin}°</span>
              </div>

              {/* Rain Probability % & Mini Bar */}
              <div className="rain-prob-group">
                <div className="rain-prob-text">
                  <Droplets size={10} />
                  <span>{item.rainProb}%</span>
                </div>
                <div className="rain-bar-track">
                  <div className="rain-bar-fill" style={{ width: `${item.rainProb}%` }}></div>
                </div>
              </div>

              {/* Severity Pill */}
              <div className={`severity-tag ${severity}`}>
                {severity === 'alert' && <AlertOctagon size={9} />}
                {severity === 'caution' && <AlertTriangle size={9} />}
                {severity === 'safe' && <ShieldCheck size={9} />}
                <span>{severity.toUpperCase()}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
