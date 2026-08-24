import React from 'react';
import { CloudSun, Globe, MapPin, ShieldAlert, Radio, PhoneCall, Sun, Moon } from 'lucide-react';

export default function Header({ currentLang, onLanguageChange, onToggleMap, onSimulateAlert, activeAlert, locationName, isSunlightMode, onToggleTheme }) {
  const handleSosCall = () => {
    window.location.href = "tel:1077";
  };

  return (
    <header className="agri-header-tworow">
      {/* Row 1: Brand, Status, SOS, Theme Toggle, Alert Sim, Language */}
      <div className="header-row-primary">
        <div className="brand-box">
          <div className="brand-logo-icon">
            <CloudSun size={22} />
          </div>
          <div>
            <h1 className="brand-title">
              Weather<span className="brand-accent">GPT</span>
            </h1>
            <span className="brand-tagline">IMD AGRI-INTELLIGENCE</span>
          </div>
        </div>

        <div className="header-controls-group">
          {/* IMD Live Status Badge */}
          <div className="badge-imd-live" title="Live IMD NWP Model Stream">
            <Radio size={12} className="pulse-icon" />
            <span>IMD LIVE</span>
          </div>

          {/* High-Contrast Light / Dark Mode Toggle */}
          <button 
            className={`btn-theme-toggle ${isSunlightMode ? 'sunlight' : ''}`}
            onClick={onToggleTheme}
            title={isSunlightMode ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {isSunlightMode ? <Sun size={14} className="sun-icon" /> : <Moon size={14} className="moon-icon" />}
            <span className="theme-text">{isSunlightMode ? 'LIGHT' : 'DARK'}</span>
          </button>

          {/* SOS 1077 Helpline Button */}
          <button 
            className="btn-header-sos" 
            onClick={handleSosCall} 
            title="Call National Disaster Helpline 1077"
          >
            <PhoneCall size={13} />
            <span>SOS 1077</span>
          </button>

          {/* Alert Simulation Trigger */}
          <button 
            className={`btn-action-alert ${activeAlert ? 'triggered' : ''}`}
            onClick={onSimulateAlert}
            title="Simulate Disaster Warning Push Alert"
          >
            <ShieldAlert size={14} />
            <span>ALERT SIM</span>
          </button>

          {/* Language Switcher */}
          <div className="lang-pill">
            <Globe size={13} className="lang-globe" />
            <select 
              value={currentLang} 
              onChange={(e) => onLanguageChange(e.target.value)}
              className="lang-select"
            >
              <option value="en">EN</option>
              <option value="hi">हिन्दी</option>
              <option value="ta">தமிழ்</option>
            </select>
          </div>
        </div>
      </div>

      {/* Row 2: Location Preview & Map Trigger */}
      <div className="header-row-secondary" onClick={onToggleMap} title="Click to open interactive district map">
        <div className="location-info-group">
          <MapPin size={15} className="pin-icon" />
          <span className="location-name">{locationName || "Coimbatore, Tamil Nadu"}</span>
          <span className="location-zone">ZONE-TN04</span>
        </div>
        <div className="map-trigger-tag">
          <span>MAP RADAR ➔</span>
        </div>
      </div>
    </header>
  );
}
