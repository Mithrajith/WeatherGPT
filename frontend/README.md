# WeatherGPT Frontend (React + Vite PWA)

This is the mobile-first Progressive Web App (PWA) for **WeatherGPT**, built using React 19, Vite 8, and standard CSS Variables.

## Features
- **Voice Mic & Waveform:** Real-time audio recording with equalizing wave bars (`.wave-bar`).
- **Crop Persona Switcher:** Paddy, Cotton, Banana, Potato, Wheat filter chips using Lucide line icons.
- **Hero 30-Day Climate Chart:** SVG rainfall anomaly chart (+45% anomaly).
- **7-Day Forecast Cards:** High/low temps, explicit rain probability %, progress bars, and risk pills.
- **In-Card Language Toggle:** In-place `EN` | `हिन्दी` | `தமிழ்` language switching without duplicate messages.
- **Emergency SOS 1077 & Alert Sim:** Direct helpline trigger and simulated WebSocket push banner.
- **Leaflet GIS Map Radar:** Interactive district weather markers & warning radius circles.
- **Dark / Light Theme Toggle:** High-contrast sunlight mode for outdoor field readability.

## Scripts
- `npm run dev`: Start local Vite dev server
- `npm run build`: Build production bundle
- `npm run preview`: Preview production build locally
