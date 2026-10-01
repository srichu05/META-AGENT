import React from 'react';
import { useApp } from '../../context/AppContext';
import { RotateCw, CheckCircle2, FlaskConical, Radio } from 'lucide-react';

export const StatusIndicator = ({ showDetails = false }) => {
  const { backendStatus, checkBackendHealth, healthInfo, isDemoMode } = useApp();

  const isConnected = backendStatus === 'connected';

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: 'var(--radius-full)',
          backgroundColor: isConnected ? 'var(--pastel-sage-bg)' : 'var(--pastel-lemon-bg)',
          border: `1px solid ${isConnected ? 'var(--pastel-sage-border)' : 'var(--pastel-lemon-border)'}`,
          color: isConnected ? 'var(--pastel-sage-text)' : 'var(--pastel-lemon-text)',
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          fontWeight: 600,
          boxShadow: 'var(--shadow-subtle)',
          transition: 'all var(--transition-fast)',
        }}
      >
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: isConnected ? '#10B981' : '#EAB308',
            display: 'inline-block',
            boxShadow: isConnected ? '0 0 8px #10B981' : '0 0 6px #EAB308',
            animation: 'softPulse 2s infinite',
          }}
        />

        <span>{isConnected ? 'API Connected' : 'Demo Mode'}</span>

        <button
          onClick={(e) => {
            e.stopPropagation();
            checkBackendHealth();
          }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            marginLeft: '2px',
            color: 'inherit',
            opacity: 0.75,
            cursor: 'pointer',
          }}
          title={isConnected ? 'Ping Kernel' : 'Retry connection to Flask 127.0.0.1:5000'}
        >
          <RotateCw size={12} />
        </button>
      </div>

      {!isConnected && (
        <span
          style={{
            fontSize: '0.725rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
            display: 'none',
          }}
        >
          (Start `python3 backend/app.py` for live API)
        </span>
      )}
    </div>
  );
};

export default StatusIndicator;
