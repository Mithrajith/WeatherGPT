// WeatherGPT Agri-Intelligence API Service Layer

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export const LIVE_STATS_MOCK = {
  location: "Coimbatore, Tamil Nadu",
  districtCode: "CBE-04",
  tempCurrent: 29,
  tempMax: 31,
  tempMin: 23,
  humidity: 78,
  rainTodayMm: 14,
  windSpeedKmh: 12,
  windDirection: "SW",
  overallSeverity: "caution"
};

export const MOCK_FORECAST_DATA = [
  { day: 'Today', tempMax: 31, tempMin: 23, rainProb: 20, rainMm: 2, condition: 'Partly Cloudy', icon: 'cloud-sun', severity: 'safe' },
  { day: 'Tomorrow', tempMax: 29, tempMin: 22, rainProb: 85, rainMm: 35, condition: 'Heavy Downpour', icon: 'cloud-rain', severity: 'alert' },
  { day: 'Wed', tempMax: 28, tempMin: 22, rainProb: 65, rainMm: 18, condition: 'Thunderstorm', icon: 'thunderstorm', severity: 'caution' },
  { day: 'Thu', tempMax: 30, tempMin: 23, rainProb: 35, rainMm: 5, condition: 'Light Shower', icon: 'cloud-drizzle', severity: 'safe' },
  { day: 'Fri', tempMax: 32, tempMin: 24, rainProb: 10, rainMm: 0, condition: 'Sunny & Clear', icon: 'sun', severity: 'safe' },
];

export const HISTORICAL_CLIMATE_TREND = [
  { period: 'W1 (Aug 1-7)', actualRain: 12, normalRain: 10 },
  { period: 'W2 (Aug 8-14)', actualRain: 28, normalRain: 15 },
  { period: 'W3 (Aug 15-21)', actualRain: 45, normalRain: 20 },
  { period: 'W4 (Aug 22-28)', actualRain: 38, normalRain: 18 },
];

export const CROP_ADVISORIES = {
  paddy: {
    cropId: 'paddy',
    cropName: '🌾 Paddy (Rice)',
    urgency: 'HIGH_ALERT',
    why: '35mm heavy rain predicted in next 24 hours cause field submergence.',
    action: 'Clear field drainage bunds immediately to prevent root rot. Suspend urea application.'
  },
  cotton: {
    cropId: 'cotton',
    cropName: '🌱 Cotton',
    urgency: 'CAUTION',
    why: 'High humidity (78%) and wet leaves encourage bollworm infestation.',
    action: 'Inspect leaf undersides for pink bollworm. Spray neem oil once rain subsides.'
  },
  banana: {
    cropId: 'banana',
    cropName: '🍌 Banana',
    urgency: 'HIGH_ALERT',
    why: 'Wind gusts up to 25 km/h with heavy downpour may cause crop lodging.',
    action: 'Provide bamboo propping support to fruiting banana trees immediately.'
  },
  potato: {
    cropId: 'potato',
    cropName: '🥔 Potato',
    urgency: 'CAUTION',
    why: 'Excess moisture increases late blight fungal disease risk.',
    action: 'Maintain strict field drainage and apply protective copper fungicide post-rain.'
  },
  wheat: {
    cropId: 'wheat',
    cropName: '🌾 Wheat',
    urgency: 'SAFE',
    why: 'Current soil moisture levels optimal for early tillering phase.',
    action: 'Proceed with normal field cultivation and monitor weekly rain forecast.'
  }
};

const MOCK_RESPONSES = {
  en: {
    coimbatore: {
      headline: "IMD District Advisory: Coimbatore, TN",
      summary: "Heavy rainfall (35 mm) forecast for tomorrow with convective gusty winds.",
      why: "Active monsoon trough shifting across Western Ghats releasing 35mm rain.",
    }
  }
};

export async function sendChatMessage({ message, language = 'en', crop = 'paddy' }) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, language, crop }),
    });
    if (!response.ok) throw new Error('API Request Failed');
    return await response.json();
  } catch (err) {
    await new Promise((resolve) => setTimeout(resolve, 500));

    const selectedAgromet = CROP_ADVISORIES[crop] || CROP_ADVISORIES.paddy;

    return {
      headline: `IMD District Advisory (${selectedAgromet.cropName})`,
      summary: `Heavy rainfall (35 mm) expected tomorrow in Coimbatore region. Tailored advisory for ${selectedAgromet.cropName} field management.`,
      why: "Monsoon trough shifting south releasing 35mm precipitation.",
      agromet: selectedAgromet,
      forecast: MOCK_FORECAST_DATA,
      stats: LIVE_STATS_MOCK,
      trend: HISTORICAL_CLIMATE_TREND
    };
  }
}

export async function sendVoiceAudio({ audioBlob, language = 'en', crop = 'paddy' }) {
  try {
    const formData = new FormData();
    if (audioBlob) formData.append('file', audioBlob, 'voice.webm');
    formData.append('language', language);
    formData.append('crop', crop);

    const response = await fetch(`${API_BASE_URL}/api/chat/voice`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('Voice API Failed');
    return await response.json();
  } catch (err) {
    await new Promise((resolve) => setTimeout(resolve, 800));

    const transcript = language === 'hi' 
      ? "कोयंबटूर वर्षा पूर्वानुमान और फसल सलाह" 
      : language === 'ta' 
      ? "கோயம்புத்தூர் மழை மற்றும் பயிர் ஆலோசனை" 
      : `Rain forecast & ${CROP_ADVISORIES[crop]?.cropName || 'Paddy'} advisory for Coimbatore`;

    const chatResult = await sendChatMessage({ message: transcript, language, crop });
    return {
      userTranscript: transcript,
      ...chatResult
    };
  }
}

export function normalizeAlert(raw) {
  if (!raw) return null;
  return {
    id: raw.alert_id || raw.id,
    district: raw.district,
    title: raw.title,
    severity: raw.severity || 'high',
    advice: raw.action || raw.advice || raw.message || '',
    validUntil: raw.valid_until || raw.validUntil
  };
}

const SEVERITY_RANK = { critical: 3, high: 2, low: 1, informational: 0 };

export function pickMostSevereAlert(alerts) {
  if (!Array.isArray(alerts) || alerts.length === 0) return null;
  return [...alerts].sort(
    (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0)
  )[0];
}

export async function fetchActiveAlerts(district) {
  if (!district) return [];
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/alerts/active?district=${encodeURIComponent(district)}`
    );
    if (!response.ok) throw new Error('Active Alerts API Failed');
    const data = await response.json();
    return (Array.isArray(data) ? data : []).map(normalizeAlert).filter(Boolean);
  } catch (err) {
    console.warn('Active alerts unavailable, continuing without banner:', err.message);
    return [];
  }
}

export function subscribeToDisasterAlerts(onAlertReceived, district = '') {
  let ws;
  let closed = false;
  const url = district
    ? `${WS_BASE_URL}/ws/alerts?district=${encodeURIComponent(district.toLowerCase())}`
    : `${WS_BASE_URL}/ws/alerts`;
  try {
    ws = new WebSocket(url);
    ws.onmessage = (event) => {
      try {
        const raw = JSON.parse(event.data);
        if (raw.severity === 'informational') return;
        const alert = normalizeAlert(raw);
        if (alert) onAlertReceived(alert);
      } catch (e) {
        console.error('Failed to parse WS alert', e);
      }
    };
    ws.onclose = () => {
      if (!closed) setTimeout(() => subscribeToDisasterAlerts(onAlertReceived, district), 5000);
    };
  } catch (e) {
    console.warn('WebSocket fallback active');
  }
  return () => {
    closed = true;
    if (ws) ws.close();
  };
}
