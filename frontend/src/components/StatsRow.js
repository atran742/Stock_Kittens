import React, { useEffect, useState } from 'react';
import './StatsRow.css';

export default function StatsRow() {
  const [stats, setStats] = useState({
    trades_tracked: '–',
    trades_this_month: '–',
    active_politicians: '–',
    politicians_last_month: '–',
    top_signal: { signal: 'HOLD', ticker: '', predicted_price: 0.0 },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('http://localhost:8000/stats');
        const data = await res.json();
        console.log('Stats data:', data);
        setStats(data);
        setError(false);
      } catch (err) {
        console.error('Fetch error:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const tradesTracked = typeof stats.trades_tracked === 'number' ? stats.trades_tracked.toLocaleString() : stats.trades_tracked;
  const tradesThisMonth = typeof stats.trades_this_month === 'number' ? stats.trades_this_month.toLocaleString() : stats.trades_this_month;
  const activePoliticians = typeof stats.active_politicians === 'number' ? stats.active_politicians.toLocaleString() : stats.active_politicians;
  const politiciansLastMonth = typeof stats.politicians_last_month === 'number' ? stats.politicians_last_month.toLocaleString() : stats.politicians_last_month;
  const topSignal = stats.top_signal || {};
  const topTicker = topSignal.ticker || '';
  const topPercent = topSignal.predicted_change !== undefined ? `${topSignal.predicted_change > 0 ? '+' : ''}${topSignal.predicted_change.toFixed(1)}%` : 'N/A';

  const cards = [
    {
      icon: '📊',
      label: 'Trades Tracked',
      value: tradesTracked,
      sub: `↑ ${tradesThisMonth} this month`,
      subClass: 'up',
    },
    {
      icon: '🏛️',
      label: 'Politicians',
      value: activePoliticians,
      sub: `${politiciansLastMonth} active last month`,
      subClass: 'hold',
    },
    {
      icon: '🎯',
      label: 'Top Signal',
      value: topSignal.signal || 'HOLD',
      sub: topTicker ? `${topTicker} · ${topPercent}` : 'No top signal',
      subClass: topSignal.signal === 'BUY' ? 'up' : topSignal.signal === 'SELL' ? 'down' : 'hold',
    },
  ];

  return (
    <div className="stats-row">
      {cards.map((s, i) => (
        <div className="stat-card" key={i}>
          <div className="stat-icon">{s.icon}</div>
          <div className="stat-label">{s.label}</div>
          <div className="stat-val">{loading ? 'Loading...' : error ? 'Error' : s.value}</div>
          <div className={`stat-sub ${s.subClass}`}>{loading ? 'Loading...' : error ? 'Backend error' : s.sub}</div>
        </div>
      ))}
    </div>
  );
}
