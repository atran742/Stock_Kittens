import React, { useState } from 'react';
import './Navbar.css';

const tabs = ['Dashboard', 'Portfolio', 'Congress', 'Predictions'];

export default function Navbar({ activeTab, setActiveTab }) {
  return (
    <nav className="navbar">
      <div className="nav-logo">
        <span className="logo-cat">🐱</span>
        Stock Kittens
        <span className="logo-badge">AI</span>
      </div>

      <div className="nav-tabs">
        {tabs.map(t => (
          <button
            key={t}
            className={`nav-tab ${activeTab === t ? 'active' : ''}`}
            onClick={() => setActiveTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="online-badge">
        <span className="pulse-dot" />
        Agent Online
      </div>
    </nav>
  );
}
