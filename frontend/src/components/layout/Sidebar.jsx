import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  Brain,
  Calculator,
  MessageSquareCode,
  SearchCode,
  BarChart3,
  Gauge,
  Database,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Layers,
  Cpu,
  Activity,
  ShieldCheck,
} from 'lucide-react';
import { StatusIndicator } from '../common/StatusIndicator';
import { ThemeToggle } from '../common/ThemeToggle';

export const Sidebar = () => {
  const { activeTab, setActiveTab, isSidebarCollapsed, setIsSidebarCollapsed } = useApp();

  const navItems = [
    {
      id: 'solver',
      label: 'Problem Solver',
      icon: Calculator,
    },
    {
      id: 'debate',
      label: 'Agent Debate',
      icon: MessageSquareCode,
    },
    {
      id: 'analysis',
      label: 'Problem Analysis',
      icon: SearchCode,
    },
    {
      id: 'stats',
      label: 'System Statistics',
      icon: BarChart3,
    },
    {
      id: 'evaluation',
      label: 'Evaluation Metrics',
      icon: Gauge,
    },
    {
      id: 'corpus',
      label: 'Knowledge Corpus',
      icon: Database,
    },
  ];

  return (
    <aside
      style={{
        width: isSidebarCollapsed ? '78px' : '290px',
        backgroundColor: 'var(--bg-card)',
        borderRight: '1px solid var(--border-default)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'width var(--transition-normal)',
        position: 'sticky',
        top: 0,
        height: '100vh',
        zIndex: 40,
        userSelect: 'none',
        boxShadow: '1px 0 10px rgba(15, 23, 42, 0.02)',
      }}
    >
      {/* Top Header / Branding */}
      <div>
        <div
          style={{
            padding: isSidebarCollapsed ? '22px 14px' : '22px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: isSidebarCollapsed ? 'center' : 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
            {/* Abstract Intelligence Mark */}
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                background: 'linear-gradient(145deg, #1E293B 0%, #0F172A 100%)',
                border: '1px solid #334155',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-electric)',
                boxShadow: '0 4px 12px rgba(15, 23, 42, 0.15)',
                flexShrink: 0,
                position: 'relative',
              }}
            >
              <Brain size={22} strokeWidth={2.2} />
              <div
                style={{
                  position: 'absolute',
                  top: '-2px',
                  right: '-2px',
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--accent-electric)',
                  boxShadow: '0 0 8px var(--accent-electric)',
                }}
              />
            </div>

            {!isSidebarCollapsed && (
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 700,
                    fontSize: '1.1rem',
                    letterSpacing: '-0.03em',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <span>META-AGENT</span>
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.675rem',
                    color: 'var(--text-muted)',
                    letterSpacing: '0.07em',
                    textTransform: 'uppercase',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  <span>THE INTELLIGENCE LAB</span>
                </div>
              </div>
            )}
          </div>

          {!isSidebarCollapsed && (
            <button
              onClick={() => setIsSidebarCollapsed(true)}
              style={{
                width: '26px',
                height: '26px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all var(--transition-fast)',
              }}
              title="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          )}
        </div>

        {/* Collapsed Expand Toggle */}
        {isSidebarCollapsed && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0' }}>
            <button
              onClick={() => setIsSidebarCollapsed(false)}
              style={{
                width: '28px',
                height: '28px',
                borderRadius: 'var(--radius-sm)',
                backgroundColor: 'var(--bg-subtle)',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title="Expand sidebar"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Navigation Items */}
        <nav style={{ padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: isSidebarCollapsed ? '12px 0' : '10px 14px',
                  justifyContent: isSidebarCollapsed ? 'center' : 'flex-start',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isActive ? 'var(--bg-subtle)' : 'transparent',
                  color: isActive ? 'var(--accent-cobalt)' : 'var(--text-secondary)',
                  border: isActive ? '1px solid var(--border-default)' : '1px solid transparent',
                  fontWeight: isActive ? 600 : 500,
                  transition: 'all var(--transition-fast)',
                  position: 'relative',
                  width: '100%',
                  textAlign: 'left',
                }}
                title={item.label}
              >
                {/* Active Indicator Bar */}
                {isActive && (
                  <span
                    style={{
                      position: 'absolute',
                      left: isSidebarCollapsed ? '3px' : '-2px',
                      top: '20%',
                      bottom: '20%',
                      width: '3.5px',
                      backgroundColor: 'var(--accent-cobalt)',
                      borderRadius: 'var(--radius-full)',
                    }}
                  />
                )}

                <div
                  style={{
                    color: isActive ? 'var(--accent-cobalt)' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Icon size={isSidebarCollapsed ? 20 : 18} />
                </div>

                {!isSidebarCollapsed && (
                  <span
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '0.92rem',
                      color: isActive ? 'var(--text-primary)' : 'inherit',
                      fontWeight: isActive ? 600 : 500,
                    }}
                  >
                    {item.label}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Clean Minimal Sidebar Footer */}
      <div
        style={{
          padding: isSidebarCollapsed ? '16px 8px' : '16px 20px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: isSidebarCollapsed ? 'center' : 'space-between',
          fontSize: '0.75rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
        }}
      >
        {!isSidebarCollapsed && <span>META-AGENT v2.0</span>}
        <span style={{ color: 'var(--status-success)', fontWeight: 600 }}>● Online</span>
      </div>
    </aside>
  );
};

export default Sidebar;
