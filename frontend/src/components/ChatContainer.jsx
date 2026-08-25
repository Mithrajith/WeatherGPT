import React, { useEffect, useRef } from 'react';
import { Volume2, Bot, User, Wrench, AlertCircle, Loader2, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const TOOL_LABELS = {
  get_current_weather: 'Checking current conditions',
  get_forecast: 'Checking forecast',
  get_district_warnings: 'Checking official warnings',
  get_farm_advisory: 'Checking farm advisory',
  get_historical_trend: 'Checking historical climate data',
  get_saved_locations: 'Looking up saved locations',
  save_location: 'Saving location',
  manage_alert_subscription: 'Updating alert subscription',
};

function toolLabel(name) {
  return TOOL_LABELS[name] || name.replace(/_/g, ' ');
}

function ToolCallPill({ call }) {
  const isRunning = call.status === 'running';
  return (
    <span className={`tool-pill ${isRunning ? 'running' : 'done'} ${call.degraded ? 'degraded' : ''}`}>
      {isRunning ? <Loader2 size={11} className="spin" /> : <Check size={11} />}
      {toolLabel(call.tool)}
    </span>
  );
}

export default function ChatContainer({ messages, isLoading, onPlayAudio }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-viewport">
      <div className="chat-scroll">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-row ${msg.sender === 'agent' ? 'from-agent' : 'from-user'}`}>
            <div className="chat-avatar">
              {msg.sender === 'agent' ? <Bot size={16} /> : <User size={16} />}
            </div>

            <div className="chat-bubble">
              {msg.toolCalls?.length > 0 && (
                <div className="tool-pill-row">
                  {msg.toolCalls.map((call, j) => <ToolCallPill key={j} call={call} />)}
                </div>
              )}

              {msg.text && (
                <div className="chat-text markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                  {msg.streaming && <span className="stream-cursor" />}
                </div>
              )}

              {!msg.text && msg.streaming && !msg.toolCalls?.length && (
                <div className="typing-dots"><span /><span /><span /></div>
              )}

              {msg.sender === 'agent' && !msg.error && !msg.streaming && msg.text && (
                <div className="chat-footer">
                  {msg.degraded && (
                    <span className="chat-tag warn" title="Answered using the Open-Meteo fallback, not an official IMD source">
                      <AlertCircle size={11} /> unofficial source
                    </span>
                  )}
                  <button className="chat-listen-btn" onClick={() => onPlayAudio(msg.text, msg.language)} title="Listen">
                    <Volume2 size={13} />
                  </button>
                  <span className="chat-time">{msg.time}</span>
                </div>
              )}
              {msg.sender === 'user' && <span className="chat-time">{msg.time}</span>}
            </div>
          </div>
        ))}

        <div ref={endRef} />
      </div>
    </div>
  );
}
