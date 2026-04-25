import React, { useEffect, useState } from 'react';
import './MarketTrends.css';

export default function MarketTrends() {
  const [indices, setIndices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchMarket = async () => {
    try {
      const res = await fetch('http://localhost:8000/market');
      const data = await res.json();
      setIndices(data.indices);
      setLastUpdated(new Date().toLocaleTimeString());
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarket();
    const interval = setInterval(fetchMarket, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="market-section">
      <div className="section-header">
        <div className="section-title">📈 Market Trends</div>
        <div className="header-right">
          {lastUpdated && <span className="updated">Updated {lastUpdated}</span>}
          <button className="refresh-btn" onClick={fetchMarket}>↻ Refresh</button>
        </div>
      </div>

      <div className="market-wrap">
        <div className="market-header">
          <span>Index</span>
          <span>Price</span>
          <span>Change</span>
          <span>% Change</span>
        </div>

        {loading && (
          <div className="market-loading">
            <span>🐱</span> Fetching live market data...
          </div>
        )}

        {error && (
          <div className="market-loading">
            😿 Could not reach backend — make sure FastAPI is running on port 8000
          </div>
        )}

        {!loading && !error && indices.map((idx, i) => (
          <div className="market-row" key={i}>
            <div>
              <div className="idx-name">{idx.name}</div>
              <div className="idx-ticker">{idx.ticker}</div>
            </div>
            <div className="idx-price">
              {idx.ticker.includes('BTC') || idx.ticker.includes('ETH')
                ? `$${idx.price.toLocaleString()}`
                : `$${idx.price.toLocaleString()}`}
            </div>
            <div className={idx.change >= 0 ? 'up' : 'down'}>
              {idx.change >= 0 ? '+' : ''}{idx.change.toLocaleString()}
            </div>
            <div className={`pct-pill ${idx.change_pct >= 0 ? 'up-pill' : 'down-pill'}`}>
              {idx.change_pct >= 0 ? '▲' : '▼'} {Math.abs(idx.change_pct)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}