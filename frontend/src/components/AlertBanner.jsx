import React from 'react';
import { AlertTriangle, Volume2, X, PhoneCall } from 'lucide-react';

export default function AlertBanner({ alert, onClose, onPlayAudio }) {
  if (!alert) return null;

  return (
    <div className={`alert-banner severity-${(alert.severity || 'high').toLowerCase()}`} role="alert">
      <AlertTriangle size={20} className="alert-icon" />

      <div className="alert-body">
        <div className="alert-meta">
          <span className="alert-district">{alert.district}</span>
          <span className="alert-sep">·</span>
          <span className="alert-severity">{alert.severity}</span>
        </div>
        <p className="alert-title">{alert.title}</p>
        {alert.advice && <p className="alert-advice">{alert.advice}</p>}
      </div>

      <div className="alert-actions">
        <button className="icon-btn" onClick={() => onPlayAudio(alert.advice || alert.title)} title="Listen">
          <Volume2 size={16} />
        </button>
        <a className="icon-btn" href="tel:1078" title="Call NDMA helpline 1078">
          <PhoneCall size={16} />
        </a>
        <button className="icon-btn" onClick={onClose} title="Dismiss" aria-label="Dismiss alert">
          <X size={16} />
        </button>
      </div>
    </div>
  );
}
