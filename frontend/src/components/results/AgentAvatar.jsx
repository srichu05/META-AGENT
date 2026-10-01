import React from 'react';
import { getAgentTheme } from '../../utils/agentTheme';

export const AgentAvatar = ({
  name = '',
  size = 'md', // 'sm' | 'md' | 'lg'
  showRole = false,
  showStatus = false,
  status = 'active', // 'active' | 'thinking' | 'idle'
}) => {
  const theme = getAgentTheme(name);

  const sizePixels = {
    sm: 28,
    md: 36,
    lg: 48,
  }[size] || 36;

  const fontSizes = {
    sm: '0.8rem',
    md: '0.95rem',
    lg: '1.25rem',
  }[size] || '0.95rem';

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
      <div
        style={{
          width: `${sizePixels}px`,
          height: `${sizePixels}px`,
          borderRadius: 'var(--radius-md)',
          backgroundColor: theme.bg,
          border: `1.5px solid ${theme.border}`,
          color: theme.text,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'var(--font-mono)',
          fontWeight: 700,
          fontSize: fontSizes,
          position: 'relative',
          flexShrink: 0,
          boxShadow: 'var(--shadow-sm)',
        }}
        title={`${theme.name} (${name})`}
      >
        <span>{theme.symbol}</span>
        {showStatus && (
          <span
            style={{
              position: 'absolute',
              bottom: '-2px',
              right: '-2px',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: status === 'active' ? '#16A34A' : '#EAB308',
              border: '1.5px solid var(--bg-card)',
            }}
          />
        )}
      </div>

      {showRole && (
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 600,
              fontSize: size === 'sm' ? '0.8rem' : '0.9rem',
              color: 'var(--text-primary)',
              lineHeight: 1.2,
            }}
          >
            {name || theme.name}
          </div>
          <div
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-body)',
              marginTop: '1px',
            }}
          >
            {theme.role}
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentAvatar;
