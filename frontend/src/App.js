import React, { useState } from 'react';
import './App.css';
import StatsRow from './components/StatsRow';
import ChatPanel from './components/ChatPanel';
import Mountains from './components/Mountains';
import MarketTrends from './components/MarketTrends';

export default function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');

  return (
    <div className="app">
      {/* <Navbar activeTab={activeTab} setActiveTab={setActiveTab} /> */}

      <div className="page-layout">
        <div className="left-panel">
          <div className="hero-banner">
            <div className="hero-text">
              <div className="hero-title">
                The<br />
                <span className="hero-accent">Stock Kittens</span> 🐾
              </div>
              <div className="hero-sub">
                Track what politicians are buying & selling 
              </div>
            </div>
            <div className="hero-cats">
            <img src={require('./assests/cute_cat.jpeg')} alt="Stock Kitten" className="hero-cat-img" />
          </div>
          </div>

          <StatsRow />
          <MarketTrends />
          {/* <ImageUpload /> */}
          <Mountains />
        </div>

        <div className="right-panel">
          <ChatPanel />
        </div>
      </div>
    </div>
  );
}
