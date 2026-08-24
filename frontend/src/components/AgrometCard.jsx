import React from 'react';
import { Sprout, AlertOctagon, CheckCircle2, AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export default function AgrometCard({ agromet }) {
  if (!agromet) return null;

  const urgency = agromet.urgency || 'SAFE';

  const getUrgencyConfig = () => {
    switch (urgency) {
      case 'HIGH_ALERT':
        return {
          badgeText: 'ACTION REQUIRED',
          badgeClass: 'badge-alert',
          icon: <AlertOctagon size={14} className="urgency-icon alert" />,
          stripClass: 'strip-alert'
        };
      case 'CAUTION':
        return {
          badgeText: 'MONITOR FIELD',
          badgeClass: 'badge-caution',
          icon: <AlertTriangle size={14} className="urgency-icon caution" />,
          stripClass: 'strip-caution'
        };
      default:
        return {
          badgeText: 'CONDITIONS SAFE',
          badgeClass: 'badge-safe',
          icon: <CheckCircle2 size={14} className="urgency-icon safe" />,
          stripClass: 'strip-safe'
        };
    }
  };

  const config = getUrgencyConfig();

  return (
    <div className={`agromet-advisory-clean ${config.stripClass}`}>
      {/* Top Meta Bar */}
      <div className="card-top-bar">
        <div className="crop-meta-box">
          <div className="crop-icon-avatar">
            <Sprout size={18} />
          </div>
          <div>
            <span className="kicker-tag">IMD AGROMET ADVISORY</span>
            <h4 className="crop-title-clean">{agromet.cropName || agromet.crop || 'Paddy (Rice)'}</h4>
          </div>
        </div>

        <div className={`urgency-pill ${config.badgeClass}`}>
          {config.icon}
          <span>{config.badgeText}</span>
        </div>
      </div>

      {/* One-Line WHY Callout */}
      <div className="why-callout-clean">
        <Info size={14} className="callout-icon" />
        <p className="why-text"><strong>Cause:</strong> {agromet.why}</p>
      </div>

      {/* Direct Action Guide */}
      <div className="action-guide-clean">
        <span className="guide-label">FIELD DIRECTIVE:</span>
        <p className="guide-text">{agromet.action}</p>
      </div>
    </div>
  );
}
