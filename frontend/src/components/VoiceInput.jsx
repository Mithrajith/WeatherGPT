import React, { useState, useRef } from 'react';
import { Mic, Send, Square, Sparkles } from 'lucide-react';

export default function VoiceInput({ onSendText, onSendVoice, isLoading, language }) {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const QUICK_PROMPTS = {
    en: ["Coimbatore Rain Tomorrow?", "Paddy Field Advisory", "Pest Risk Warning"],
    hi: ["कोयंबटूर में कल बारिश?", "धान फसल सलाह", "कीट जोखिम चेतावनी"],
    ta: ["நாளை கோயம்புத்தூர் மழை?", "நெல் பயிர் ஆலோசனை", "பூச்சி தாக்குதல் எச்சரிக்கை"]
  };

  const currentPrompts = QUICK_PROMPTS[language] || QUICK_PROMPTS.en;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!text.trim() || isLoading) return;
    onSendText(text.trim());
    setText('');
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        onSendVoice(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (err) {
      console.warn('Mic fallback engaged:', err);
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        onSendVoice(null);
      }, 2500);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="rural-field-input-bar">
      {/* Quick Prompt Chips */}
      <div className="quick-prompt-row">
        <Sparkles size={13} className="sparkle-gold" />
        {currentPrompts.map((prompt, i) => (
          <button 
            key={i} 
            className="chip-prompt-btn"
            onClick={() => onSendText(prompt)}
            disabled={isLoading || isRecording}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Live Voice Recording Waveform Overlay */}
      {isRecording && (
        <div className="recording-waveform-banner">
          <span className="rec-live-dot"></span>
          <span className="rec-text">Listening in native language...</span>
          <div className="waveform-bars flex-row">
            <span className="wave-bar b1"></span>
            <span className="wave-bar b2"></span>
            <span className="wave-bar b3"></span>
            <span className="wave-bar b4"></span>
            <span className="wave-bar b5"></span>
            <span className="wave-bar b6"></span>
          </div>
          <button className="btn-stop-rec" onClick={stopRecording}>
            <Square size={14} /> Stop
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-field-group">
        {/* Extra Large 52px Glowing Mic Button */}
        <button
          type="button"
          className={`btn-large-mic ${isRecording ? 'active-rec' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isLoading}
          title={isRecording ? "Stop recording" : "Speak in local language"}
        >
          {isRecording ? <Square size={22} /> : <Mic size={24} />}
          {isRecording && <div className="pulse-aura"></div>}
        </button>

        {/* High-Contrast Input Field */}
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            isRecording
              ? "Listening to voice..."
              : language === 'hi'
              ? "मौसम या फसल सुरक्षा के बारे में पूछें..."
              : language === 'ta'
              ? "வானிலை அல்லது பயிர் பற்றி கேட்கவும்..."
              : "Ask weather or crop advisory in any Indian language..."
          }
          className="field-text-input"
          disabled={isLoading || isRecording}
        />

        {/* High-Contrast Send Button */}
        <button
          type="submit"
          className="btn-field-send"
          disabled={!text.trim() || isLoading || isRecording}
          title="Send query"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
}
