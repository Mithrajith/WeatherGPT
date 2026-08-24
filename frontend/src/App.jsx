import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LiveStatsStrip from './components/LiveStatsStrip';
import CropSelector from './components/CropSelector';
import AlertBanner from './components/AlertBanner';
import ChatContainer from './components/ChatContainer';
import VoiceInput from './components/VoiceInput';
import MapModal from './components/MapModal';
import { sendChatMessage, sendVoiceAudio, subscribeToDisasterAlerts, MOCK_FORECAST_DATA, LIVE_STATS_MOCK, CROP_ADVISORIES, HISTORICAL_CLIMATE_TREND } from './services/api';
import './App.css';

const INITIAL_MESSAGES = {
  en: {
    headline: "IMD Agri-Intelligence Directive Ready",
    text: "Namaste! I am WeatherGPT, connected to live India Meteorological Department (IMD) APIs. Ask me about weather forecasts, rainfall, or crop safety advisories in your local language.",
    why: "Monsoon convection trough currently active across Western Ghats releasing precipitation.",
    forecast: MOCK_FORECAST_DATA,
    agromet: CROP_ADVISORIES.paddy,
    trend: HISTORICAL_CLIMATE_TREND
  },
  hi: {
    headline: "आईएमडी कृषि-इंटेलिजेंस निर्देश तैयार है",
    text: "नमस्ते! मैं WeatherGPT हूँ, लाइव भारत मौसम विज्ञान विभाग (IMD) एपीआई से जुड़ा हुआ। आप मुझसे अपनी स्थानीय भाषा में मौसम, बारिश या फसल सुरक्षा के बारे में पूछ सकते हैं।",
    why: "पश्चिमी घाट पर मानसून द्रोणिका सक्रिय है।",
    forecast: MOCK_FORECAST_DATA,
    agromet: CROP_ADVISORIES.paddy,
    trend: HISTORICAL_CLIMATE_TREND
  },
  ta: {
    headline: "IMD வேளாண்-உளவு வழிகாட்டுதல் தயார்",
    text: "வணக்கம்! நான் WeatherGPT, நேரலை இந்திய வானிலை துறை (IMD) API உடன் இணைக்கப்பட்டுள்ளேன். வானிலை, மழை மற்றும் பயிர் பாதுகாப்பு பற்றிய கேள்விகளை கேட்கலாம்.",
    why: "மேற்குத் தொடர்ச்சி மலையில் பருவமழை தீவிரம்.",
    forecast: MOCK_FORECAST_DATA,
    agromet: CROP_ADVISORIES.paddy,
    trend: HISTORICAL_CLIMATE_TREND
  }
};

export default function App() {
  const [language, setLanguage] = useState('en');
  const [activeCrop, setActiveCrop] = useState('paddy');
  const [isSunlightMode, setIsSunlightMode] = useState(false);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [activeAlert, setActiveAlert] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [liveStats, setLiveStats] = useState(LIVE_STATS_MOCK);
  
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      ...INITIAL_MESSAGES.en,
      time: '12:00 PM'
    }
  ]);

  const handleLanguageChange = (newLang) => {
    setLanguage(newLang);
    const updatedContent = INITIAL_MESSAGES[newLang] || INITIAL_MESSAGES.en;

    setMessages((prev) => {
      const newArr = [...prev];
      const lastIndex = newArr.map(m => m.sender).lastIndexOf('agent');
      if (lastIndex !== -1) {
        newArr[lastIndex] = {
          ...newArr[lastIndex],
          headline: updatedContent.headline,
          text: updatedContent.text,
          why: updatedContent.why
        };
      }
      return newArr;
    });

    speakText(updatedContent.text, newLang);
  };

  const handleCropChange = (cropId) => {
    setActiveCrop(cropId);
    const updatedAgromet = CROP_ADVISORIES[cropId] || CROP_ADVISORIES.paddy;
    
    setMessages((prev) => {
      const newArr = [...prev];
      const lastIndex = newArr.map(m => m.sender).lastIndexOf('agent');
      if (lastIndex !== -1) {
        newArr[lastIndex] = {
          ...newArr[lastIndex],
          agromet: updatedAgromet
        };
      }
      return newArr;
    });

    speakText(`Crop advisory updated for ${updatedAgromet.cropName}`, language);
  };

  useEffect(() => {
    const unsubscribe = subscribeToDisasterAlerts((alertData) => {
      setActiveAlert(alertData);
    });
    return unsubscribe;
  }, []);

  const handleSendText = async (queryText) => {
    const userMsg = {
      sender: 'user',
      text: queryText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const result = await sendChatMessage({ message: queryText, language, crop: activeCrop });
      
      const agentMsg = {
        sender: 'agent',
        headline: result.headline,
        text: result.summary,
        why: result.why,
        agromet: result.agromet,
        forecast: result.forecast,
        trend: result.trend,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, agentMsg]);
      speakText(result.summary, language);
    } catch (err) {
      console.error('Error fetching chat response:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendVoice = async (audioBlob) => {
    setIsLoading(true);
    try {
      const result = await sendVoiceAudio({ audioBlob, language, crop: activeCrop });
      
      const userMsg = {
        sender: 'user',
        text: `🎙️ "${result.userTranscript}"`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const agentMsg = {
        sender: 'agent',
        headline: result.headline,
        text: result.summary,
        why: result.why,
        agromet: result.agromet,
        forecast: result.forecast,
        trend: result.trend,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, userMsg, agentMsg]);
      speakText(result.summary, language);
    } catch (err) {
      console.error('Error handling voice audio:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const speakText = (textToSpeak, lang) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = lang === 'hi' ? 'hi-IN' : lang === 'ta' ? 'ta-IN' : 'en-IN';
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
  };

  const handleSimulateAlert = () => {
    if (activeAlert) {
      setActiveAlert(null);
    } else {
      setActiveAlert({
        title: "IMD RED ALERT: HEAVY RAINFALL WARNING",
        severity: "HIGH",
        district: "Coimbatore / Tamil Nadu",
        advice: "Convective rainfall exceeding 35mm predicted in 6 hours. Farmers: Clear field drainage channels immediately to prevent paddy submergence."
      });
      speakText("IMD Red Alert triggered for Coimbatore district. SOS helpline 1077 active.", language);
    }
  };

  return (
    <div className={`agri-app-viewport ${isSunlightMode ? 'theme-sunlight-bg' : ''}`}>
      <div className="agri-shell" data-theme={isSunlightMode ? 'sunlight' : 'dark'}>
        {/* 2-Row Header */}
        <Header 
          currentLang={language}
          onLanguageChange={handleLanguageChange}
          onToggleMap={() => setIsMapOpen(true)}
          onSimulateAlert={handleSimulateAlert}
          activeAlert={activeAlert}
          locationName={liveStats.location}
          isSunlightMode={isSunlightMode}
          onToggleTheme={() => setIsSunlightMode(!isSunlightMode)}
        />

        {/* Glanceable Live Data Top Strip */}
        <LiveStatsStrip stats={liveStats} />

        {/* Crop Selector Bar */}
        <CropSelector activeCrop={activeCrop} onCropSelect={handleCropChange} />

        {/* Emergency Alert Banner with SOS Helpline 1077 */}
        <AlertBanner 
          alert={activeAlert} 
          onClose={() => setActiveAlert(null)} 
          onPlayAudio={(advice) => speakText(advice, language)} 
        />

        {/* Main Assistant Chat Stream */}
        <main className="agri-main">
          <ChatContainer 
            messages={messages} 
            isLoading={isLoading} 
            onPlayAudio={(text, lang) => speakText(text, lang || language)}
            language={language}
            onLanguageChange={handleLanguageChange}
          />
        </main>

        {/* High-Contrast Field Voice Input */}
        <VoiceInput 
          onSendText={handleSendText} 
          onSendVoice={handleSendVoice} 
          isLoading={isLoading}
          language={language}
        />

        {/* District Map Overlay */}
        <MapModal 
          isOpen={isMapOpen} 
          onClose={() => setIsMapOpen(false)} 
        />
      </div>
    </div>
  );
}
