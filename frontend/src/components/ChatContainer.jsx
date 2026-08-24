import React, { useEffect, useRef } from 'react';
import { Volume2, Bot, User, Sparkles, Info, Globe } from 'lucide-react';
import AgrometCard from './AgrometCard';
import ForecastWidget from './ForecastWidget';
import ClimateTrendChart from './ClimateTrendChart';

export default function ChatContainer({ messages, isLoading, onPlayAudio, language, onLanguageChange }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-viewport">
      <div className="chat-scroll-area">
        {messages.map((msg, index) => {
          const isAgent = msg.sender === 'agent';
          return (
            <div key={index} className={`chat-row ${isAgent ? 'agent-row' : 'user-row'}`}>
              <div className="avatar-box">
                {isAgent ? <Bot size={18} /> : <User size={18} />}
              </div>

              <div className="chat-bubble-group">
                {/* User Message Bubble */}
                {!isAgent && (
                  <div className="bubble user-bubble">
                    <p>{msg.text}</p>
                  </div>
                )}

                {/* Structured Agent Response Card */}
                {isAgent && (
                  <div className="agent-structured-card">
                    {/* Header with Headline & In-Card Language Switcher */}
                    <div className="agent-card-header">
                      <div className="headline-group">
                        <Sparkles size={14} className="sparkle-icon" />
                        <span className="agent-headline">{msg.headline || "IMD AGRI-INTELLIGENCE DIRECTIVE"}</span>
                      </div>

                      {/* In-Card Language Toggle Pill */}
                      <div className="card-lang-toggle" title="Switch response language">
                        <Globe size={12} />
                        <button 
                          className={`lang-btn ${language === 'en' ? 'active' : ''}`}
                          onClick={() => onLanguageChange('en')}
                        >
                          EN
                        </button>
                        <button 
                          className={`lang-btn ${language === 'hi' ? 'active' : ''}`}
                          onClick={() => onLanguageChange('hi')}
                        >
                          हिन्दी
                        </button>
                        <button 
                          className={`lang-btn ${language === 'ta' ? 'active' : ''}`}
                          onClick={() => onLanguageChange('ta')}
                        >
                          தமிழ்
                        </button>
                      </div>
                    </div>

                    {/* Summary Text Body */}
                    <div className="agent-card-body">
                      <p className="summary-text">{msg.text || msg.summary}</p>

                      {/* One-Line WHY Callout */}
                      {msg.why && (
                        <div className="why-callout-inline">
                          <Info size={14} className="callout-icon" />
                          <span><strong>Meteorological Cause:</strong> {msg.why}</span>
                        </div>
                      )}
                    </div>

                    {/* Audio Play Action Bar */}
                    <div className="agent-card-actions">
                      <button 
                        className="btn-tts-listen"
                        onClick={() => onPlayAudio(msg.text || msg.summary, language)}
                        title="Listen audio in selected Indian language"
                      >
                        <Volume2 size={15} />
                        <span>Listen Voice Audio</span>
                      </button>
                      <span className="msg-time">{msg.time || 'Just now'}</span>
                    </div>

                    {/* Structured Agromet Advisory Card */}
                    {msg.agromet && (
                      <AgrometCard agromet={msg.agromet} />
                    )}

                    {/* 30-Day Climate Trend Mini Chart (Hero Visualization) */}
                    {msg.trend && (
                      <ClimateTrendChart trend={msg.trend} />
                    )}

                    {/* 7-Day Forecast Visualization */}
                    {msg.forecast && (
                      <ForecastWidget forecast={msg.forecast} />
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Loading / Agent Thinking State */}
        {isLoading && (
          <div className="chat-row agent-row loading-row">
            <div className="avatar-box">
              <Bot size={18} />
            </div>
            <div className="agent-structured-card loading-card">
              <div className="pulse-loader">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className="loading-txt">Querying IMD GFS/WRF model grids...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
