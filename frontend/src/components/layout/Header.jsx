import React from 'react';
import { useApp } from '../../context/AppContext';
import { Sparkles, ArrowRight, ShieldCheck } from 'lucide-react';

export const Header = ({ onNavigateSection }) => {
  const { activeTab, setActiveTab, backendStatus } = useApp();

  const navItems = [
    { id: 'solver', label: 'Problem Solver' },
    { id: 'debate', label: 'Agent Debate' },
    { id: 'analysis', label: 'Analysis' },
    { id: 'stats', label: 'Telemetry' },
    { id: 'evaluation', label: 'Evaluation' },
    { id: 'corpus', label: 'Corpus' },
  ];

  const handleNavClick = (id) => {
    setActiveTab(id);
    if (onNavigateSection) {
      onNavigateSection(id);
    } else {
      const el = document.getElementById('workbench-section');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backgroundColor: 'rgba(5, 5, 5, 0.82)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <div
        className="ssych-container"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '24px',
        }}
      >
        {/* Brand / Logo */}
        <div
          onClick={() => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            cursor: 'pointer',
            textDecoration: 'none',
          }}
        >
          {/* Exact Geometric Double-Glyph Logo Mark */}
          <div
            style={{
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
              <path
                d="M4 8L14 3L24 8L14 13L4 8Z"
                fill="url(#logo_grad1)"
                stroke="rgba(255,255,255,0.8)"
                strokeWidth="0.75"
              />
              <path
                d="M4 14L14 19L24 14L14 9L4 14Z"
                fill="url(#logo_grad2)"
                stroke="rgba(255,255,255,0.6)"
                strokeWidth="0.75"
              />
              <path
                d="M4 20L14 25L24 20L14 15L4 20Z"
                fill="url(#logo_grad3)"
                stroke="rgba(255,255,255,0.4)"
                strokeWidth="0.75"
              />
              <defs>
                <linearGradient id="logo_grad1" x1="4" y1="3" x2="24" y2="13" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#FFFFFF" />
                  <stop offset="1" stopColor="#94A3B8" />
                </linearGradient>
                <linearGradient id="logo_grad2" x1="4" y1="9" x2="24" y2="19" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#CBD5E1" />
                  <stop offset="1" stopColor="#64748B" />
                </linearGradient>
                <linearGradient id="logo_grad3" x1="4" y1="15" x2="24" y2="25" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#94A3B8" />
                  <stop offset="1" stopColor="#334155" />
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span
            style={{
              fontFamily: 'var(--font-sans)',
              fontSize: '1.05rem',
              fontWeight: 700,
              letterSpacing: '-0.025em',
              color: '#FFFFFF',
            }}
          >
            META-AGENT
          </span>
        </div>

        {/* Center Navigation Links */}
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '28px',
          }}
        >
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => handleNavClick(item.id)}
                style={{
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  color: isActive ? '#FFFFFF' : '#A1A1AA',
                  transition: 'color var(--transition-fast)',
                  padding: '4px 0',
                  position: 'relative',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.color = '#A1A1AA';
                }}
              >
                {item.label}
                {isActive && (
                  <span
                    style={{
                      position: 'absolute',
                      bottom: '-2px',
                      left: 0,
                      right: 0,
                      height: '1px',
                      backgroundColor: '#FFFFFF',
                    }}
                  />
                )}
              </button>
            );
          })}
        </nav>

        {/* Right CTA Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* Backend Status Pill */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '9999px',
              background: '#0E0E0E',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              fontSize: '0.75rem',
              fontFamily: 'var(--font-mono)',
              color: backendStatus === 'connected' ? '#10B981' : '#A1A1AA',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: backendStatus === 'connected' ? '#10B981' : '#71717A',
                boxShadow: backendStatus === 'connected' ? '0 0 8px #10B981' : 'none',
              }}
            />
            <span>{backendStatus === 'connected' ? 'Kernel 5000' : 'Demo Mode'}</span>
          </div>

          {/* Pure White Rounded Pill Button (Identical to reference Get started ->) */}
          <button
            onClick={() => handleNavClick('solver')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#FFFFFF',
              color: '#000000',
              fontWeight: 600,
              fontSize: '0.84rem',
              padding: '7px 16px',
              borderRadius: '9999px',
              transition: 'opacity var(--transition-fast), transform var(--transition-fast)',
              letterSpacing: '-0.01em',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = '0.92';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <span>Launch Solver</span>
            <ArrowRight size={13} strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
