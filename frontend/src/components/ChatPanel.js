import React, { useState, useRef, useEffect } from 'react';
import './ChatPanel.css';

const SUGGESTIONS = [
  "What did Pelosi buy?",
  "NVDA prediction",
  "All recent trades",
  "AAPL performance",
  "Who's trading Tesla?",
];

const CATS = ['😸', '😺', '🐱', '😻', '🐾'];
const randomCat = () => CATS[Math.floor(Math.random() * CATS.length)];

const INITIAL_MESSAGES = [
  {
    role: 'agent',
    text: "Meow! I'm Whiskers 🐾\n\nAsk me about stock performances or price predictions. I'll fetch real data and give you the purrfect analysis!",
    cat: '😸',
  },
];

export default function ChatPanel() {
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const msgsRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const send = async (text) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: msg }]);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'agent',
        text: data.response || 'Meow... something went wrong 🐾',
        cat: randomCat(),
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'agent',
        text: "Purrr... can't reach the backend! Make sure FastAPI is running on port 8000 🐱",
        cat: '😿',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat-card">
      <div className="chat-header">
        
          🐈‍⬛
        <div>
          <div className="chat-title">Whiskers AI</div>
          <div className="chat-subtitle">Your AI Agent stock analyst</div>
        </div>
      </div>

      <div className="chat-msgs" ref={msgsRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="msg-av">{m.role === 'agent' ? (m.cat || '😸') : '👤'}</div>
            <div className="msg-bub">{m.text}</div>
          </div>
        ))}
        {loading && (
          <div className="msg agent">
            <div className="msg-av">
              <image>

              </image>
            </div>
            <div className="msg-bub">
              <div className="typing-dots">
                <span /><span /><span />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="suggestions">
        {SUGGESTIONS.map((s, i) => (
          <button key={i} className="sug" onClick={() => send(s)}>{s}</button>
        ))}
      </div>

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Ask Whiskers anything..."
          rows={1}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
        />
        <button className="send-btn" onClick={() => send()}>➤</button>
      </div>
    </div>
  );
}
