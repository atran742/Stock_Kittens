import React from 'react';
import './Mountains.css';

export default function Mountains() {
  return (
    <div className="mountains">
      <svg viewBox="0 0 1200 120" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M0,80 L60,20 L120,60 L180,10 L240,50 L300,5 L360,45 L420,15 L480,55 L540,0 L600,40 L660,10 L720,50 L780,20 L840,60 L900,15 L960,55 L1020,25 L1080,65 L1140,30 L1200,70 L1200,120 L0,120Z"
          fill="rgba(255,253,245,0.55)"
        />
        <path
          d="M0,100 L80,50 L160,80 L240,30 L320,70 L400,40 L480,75 L560,25 L640,65 L720,35 L800,70 L880,45 L960,80 L1040,50 L1120,85 L1200,55 L1200,120 L0,120Z"
          fill="rgba(255,253,245,0.35)"
        />
      </svg>
    </div>
  );
}
