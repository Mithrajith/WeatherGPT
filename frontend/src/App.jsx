import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatPage from './pages/ChatPage';
import AlertsPage from './pages/AlertsPage';
import DashboardPage from './pages/DashboardPage';
import { fetchTTS, checkBackendHealth } from './services/api';
import { stripMarkdownForSpeech } from './utils/stripMarkdown';
import './App.css';

export default function App() {
  const [language, setLanguage] = useState('auto');
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const ok = await checkBackendHealth();
      if (!cancelled) setIsBackendConnected(ok);
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const handleLanguageChange = useCallback((newLang) => {
    setLanguage(newLang);
  }, []);

  const playAudio = useCallback(async (text, lang = 'en') => {
    const spoken = stripMarkdownForSpeech(text);
    if (!spoken) return;
    const audioUrl = await fetchTTS({ text: spoken, language: lang });
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.playbackRate = 1.15;
      audio.play().catch(() => {});
      return;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(spoken);
      const voiceLang = { hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', kn: 'kn-IN', bn: 'bn-IN' }[lang] || 'en-IN';
      utterance.lang = voiceLang;
      utterance.rate = 1.15;
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  return (
    <BrowserRouter>
      <div className="app-frame">
        <Sidebar
          language={language}
          onLanguageChange={handleLanguageChange}
          isBackendConnected={isBackendConnected}
          alertCount={alertCount}
        />

        <div className="app-shell">
          <main className="agri-main">
            <Routes>
              <Route path="/" element={<ChatPage language={language} />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route
                path="/alerts"
                element={<AlertsPage onPlayAudio={playAudio} onAlertsCount={setAlertCount} />}
              />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
