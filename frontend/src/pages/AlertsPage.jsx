import React, { useEffect, useState } from 'react';
import { AlertTriangle, PhoneCall, Volume2, RefreshCw } from 'lucide-react';
import { fetchRecentAlerts, subscribeToDisasterAlerts } from '../services/api';

function AlertCard({ alert, onPlayAudio }) {
  const severity = (alert.severity || 'high').toLowerCase();
  return (
    <div className={`alert-card severity-${severity}`}>
      <div className="alert-card-icon">
        <AlertTriangle size={18} />
      </div>
      <div className="alert-card-body">
        <div className="alert-card-meta">
          <span className="alert-district">{alert.district}</span>
          <span className="alert-sep">·</span>
          <span className="alert-severity">{alert.severity}</span>
          {alert.validUntil && (
            <>
              <span className="alert-sep">·</span>
              <span className="alert-until">
                until {new Date(alert.validUntil).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
              </span>
            </>
          )}
        </div>
        <p className="alert-card-title">{alert.title}</p>
        {alert.advice && <p className="alert-card-advice">{alert.advice}</p>}
      </div>
      <div className="alert-card-actions">
        <button className="icon-btn" onClick={() => onPlayAudio(alert.advice || alert.title)} title="Listen">
          <Volume2 size={15} />
        </button>
        <a className="icon-btn" href="tel:1078" title="Call NDMA helpline 1078">
          <PhoneCall size={15} />
        </a>
      </div>
    </div>
  );
}

export default function AlertsPage({ onPlayAudio, onAlertsCount }) {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    setIsLoading(true);
    const data = await fetchRecentAlerts(50);
    setAlerts(data);
    setError(data.length === 0);
    setIsLoading(false);
    onAlertsCount?.(data.length);
  };

  useEffect(() => {
    load();
    // Live push: any newly broadcast alert (heavy rain, cyclone, etc.) is
    // prepended immediately instead of waiting for the next poll/refresh.
    const unsubscribe = subscribeToDisasterAlerts((incoming) => {
      setAlerts((prev) => {
        if (prev.some((a) => a.id === incoming.id)) return prev;
        const next = [incoming, ...prev];
        onAlertsCount?.(next.length);
        return next;
      });
    });
    return unsubscribe;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="alerts-page">
      <div className="alerts-page-header">
        <h2>Active Weather Alerts</h2>
        <button className="refresh-btn" onClick={load} title="Refresh">
          <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
        </button>
      </div>

      {isLoading && alerts.length === 0 && (
        <div className="alerts-empty">Loading alerts…</div>
      )}

      {!isLoading && alerts.length === 0 && (
        <div className="alerts-empty">
          <AlertTriangle size={28} />
          <p>No active warnings right now. You'll see heavy rain, cyclone, or heatwave alerts here as soon as they're issued.</p>
        </div>
      )}

      <div className="alerts-list">
        {alerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} onPlayAudio={onPlayAudio} />
        ))}
      </div>

      {error && alerts.length === 0 && (
        <p className="alerts-error-note">Couldn't reach the alerts service. Make sure the backend is running.</p>
      )}
    </div>
  );
}
