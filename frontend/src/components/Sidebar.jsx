import React from 'react';
import { NavLink } from 'react-router-dom';
import { CloudSun, Globe, PhoneCall, MessageCircle, AlertTriangle, LayoutDashboard } from 'lucide-react';

const LANGUAGES = [
  { code: 'auto', label: 'Auto' },
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'bn', label: 'বাংলা' },
];

// Single nav surface for every screen size: a left rail on desktop, a
// compact top bar on mobile (see the `@media (max-width: 767px)` rules in
// App.css) — no separate Header/NavBar components.
export default function Sidebar({ language, onLanguageChange, isBackendConnected, alertCount = 0 }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <CloudSun size={22} className="brand-icon" />
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <MessageCircle size={18} />
          <span>Chat</span>
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/alerts" className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}>
          <span className="nav-icon-wrap">
            <AlertTriangle size={18} />
            {alertCount > 0 && <span className="nav-badge">{alertCount > 9 ? '9+' : alertCount}</span>}
          </span>
          <span>Alerts</span>
        </NavLink>
      </nav>

      <div className="sidebar-spacer" />

      <div className="sidebar-section">
        <label className="sidebar-label">
          <Globe size={13} /> Language
        </label>
        <div className="lang-select-wrap sidebar-lang">
          <select
            value={language}
            onChange={(e) => onLanguageChange(e.target.value)}
            className="lang-select"
            aria-label="Response language"
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="sidebar-section sidebar-status-row">
        <div className={`connection-pill ${isBackendConnected ? 'online' : 'offline'}`}>
          <span className="connection-dot" />
          <span className="connection-label">{isBackendConnected ? 'Connected' : 'Offline'}</span>
        </div>

        <a href="tel:1078" className="sos-link sidebar-sos" title="NDMA disaster helpline">
          <PhoneCall size={14} />
          <span>1078</span>
        </a>
      </div>
    </aside>
  );
}
