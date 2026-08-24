import React from 'react';
import { AlertTriangle, Volume2, X, PhoneCall } from 'lucide-react';

export default function AlertBanner({ alert, onClose, onPlayAudio }) {
  if (!alert) return null;

  const handleSosCall = () => {
    window.location.href = "tel:1077";
  };

  return (
    <div className={`disaster-alert-banner severity-${alert.severity?.toLowerCase() || 'high'}`}>
      <div className="alert-content-wrapper">
        <div className="alert-icon-box">
          <AlertTriangle className="alert-flash-icon" size={24} />
        </div>
        <div className="alert-details">
          <div className="alert-header">
            <span className="alert-tag">IMD EMERGENCY ALERT</span>
            <span className="alert-district">{alert.district || 'Coimbatore / Tamil Nadu'}</span>
          </div>
          <h3 className="alert-title">{alert.title || 'HEAVY RAINFALL & FLASH FLOOD WARNING'}</h3>
          <p className="alert-advice">{alert.advice || 'Severe convective storms predicted in next 6 hours. Farmers advise: Drain excess water from fields.'}</p>
        </div>
      </div>

      <div className="alert-actions">
        {/* SOS Disaster Helpline Button */}
        <button className="btn-alert-sos" onClick={handleSosCall} title="Call National Disaster Helpline 1077">
          <PhoneCall size={14} />
          <span>SOS 1077</span>
        </button>

        {/* Listen Warning Audio */}
        <button className="btn-alert-audio" onClick={() => onPlayAudio(alert.advice)}>
          <Volume2 size={14} />
          <span>Listen Audio</span>
        </button>
        
        <button className="btn-alert-close" onClick={onClose} aria-label="Dismiss Alert">
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
