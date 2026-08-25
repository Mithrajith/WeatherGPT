import React, { useState, useRef } from 'react';
import { Mic, Send, Square } from 'lucide-react';

const PLACEHOLDER = {
  en: 'Ask about weather, warnings, or farming advice…',
  hi: 'मौसम, चेतावनी या खेती सलाह के बारे में पूछें…',
  ta: 'வானிலை, எச்சரிக்கை அல்லது வேளாண் ஆலோசனை பற்றி கேளுங்கள்…',
  te: 'వాతావరణం, హెచ్చరికలు లేదా వ్యవసాయ సలహా గురించి అడగండి…',
  kn: 'ಹವಾಮಾನ, ಎಚ್ಚರಿಕೆಗಳು ಅಥವಾ ಕೃಷಿ ಸಲಹೆ ಬಗ್ಗೆ ಕೇಳಿ…',
  bn: 'আবহাওয়া, সতর্কতা বা কৃষি পরামর্শ সম্পর্কে জিজ্ঞাসা করুন…',
};

export default function VoiceInput({ onSendText, onSendVoice, isLoading, language }) {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

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
      console.warn('Microphone unavailable:', err.message);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <div className="input-bar">
      {isRecording && (
        <div className="recording-indicator">
          <span className="rec-dot" />
          <span>Listening…</span>
          <button className="stop-rec-btn" onClick={stopRecording}>
            <Square size={12} /> Stop
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-form">
        <button
          type="button"
          className={`mic-btn ${isRecording ? 'recording' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isLoading}
          title={isRecording ? 'Stop recording' : 'Speak your question'}
        >
          {isRecording ? <Square size={18} /> : <Mic size={18} />}
        </button>

        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={isRecording ? 'Listening…' : (PLACEHOLDER[language] || PLACEHOLDER.en)}
          className="text-input"
          disabled={isLoading || isRecording}
        />

        <button
          type="submit"
          className="send-btn"
          disabled={!text.trim() || isLoading || isRecording}
          title="Send"
        >
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
