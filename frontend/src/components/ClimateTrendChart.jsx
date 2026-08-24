import React, { useState } from 'react';
import { BarChart3, TrendingUp, Info } from 'lucide-react';

export default function ClimateTrendChart({ trend }) {
  const [activeBar, setActiveBar] = useState(null);

  if (!trend || trend.length === 0) return null;

  const maxVal = 50;

  return (
    <div className="climate-trend-hero-card">
      <div className="trend-hero-header">
        <div className="title-block">
          <BarChart3 size={18} className="hero-chart-icon" />
          <div>
            <h4 className="hero-title">30-DAY DISTRICT RAINFALL ANOMALY</h4>
            <span className="hero-subtitle">IMD Historical Baseline vs 2026 Observed</span>
          </div>
        </div>
        <div className="anomaly-hero-badge">
          <TrendingUp size={14} />
          <span>+45% ANOMALY</span>
        </div>
      </div>

      <div className="hero-chart-wrapper">
        <div className="chart-legend-row">
          <div className="legend-chip actual">
            <span className="chip-color teal"></span>
            <span>2026 Actual Rain (mm)</span>
          </div>
          <div className="legend-chip normal">
            <span className="chip-line amber"></span>
            <span>10-Yr Historical Normal</span>
          </div>
        </div>

        {/* Hero SVG Chart */}
        <svg viewBox="0 0 340 120" className="hero-chart-svg">
          {/* Y Axis Grid & Labels */}
          <line x1="35" y1="20" x2="330" y2="20" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <text x="5" y="23" className="y-axis-label">50mm</text>

          <line x1="35" y1="55" x2="330" y2="55" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
          <text x="5" y="58" className="y-axis-label">25mm</text>

          <line x1="35" y1="90" x2="330" y2="90" stroke="rgba(255,255,255,0.15)" />
          <text x="15" y="93" className="y-axis-label">0mm</text>

          {/* Bar Columns & Normal Markers */}
          {trend.map((item, idx) => {
            const x = 70 + idx * 70;
            const barHeight = (item.actualRain / maxVal) * 70;
            const barY = 90 - barHeight;
            const normalY = 90 - (item.normalRain / maxVal) * 70;
            const isHovered = activeBar === idx;

            return (
              <g 
                key={idx} 
                className="chart-col-group"
                onMouseEnter={() => setActiveBar(idx)}
                onMouseLeave={() => setActiveBar(null)}
              >
                {/* Bar */}
                <rect
                  x={x - 14}
                  y={barY}
                  width="28"
                  height={barHeight}
                  rx="6"
                  className={`hero-bar-rect ${isHovered ? 'hovered' : ''}`}
                />
                
                {/* Value Label */}
                <text x={x} y={barY - 5} textAnchor="middle" className="hero-bar-val">
                  {item.actualRain}mm
                </text>

                {/* Normal Dot & Line Connector */}
                <line x1={x - 14} y1={normalY} x2={x + 14} y2={normalY} stroke="var(--alert-amber)" strokeWidth="2.5" strokeDasharray="2 2" />
                <circle cx={x} cy={normalY} r="3" className="normal-marker-dot" />

                {/* X Axis Week Label */}
                <text x={x} y="106" textAnchor="middle" className="hero-x-label">
                  {item.period.split(' ')[0]}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="hero-insight-footer">
        <Info size={14} className="insight-icon" />
        <span><strong>Climate Directive:</strong> August precipitation exceeds 10-year baseline by <strong>45%</strong>. Fungal spore germination risk is CRITICAL for Paddy & Cotton crops.</span>
      </div>
    </div>
  );
}
