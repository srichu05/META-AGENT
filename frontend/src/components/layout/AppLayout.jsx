import React from 'react';
import { Header } from './Header';
import { ToastContainer } from '../common/Toast';

export const AppLayout = ({ children, onNavigateSection }) => {
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-canvas)',
        color: 'var(--text-primary)',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Precision Sticky Top Navbar (Directly from reference) */}
      <Header onNavigateSection={onNavigateSection} />

      {/* Main Content Area */}
      <main
        style={{
          flex: 1,
          width: '100%',
          position: 'relative',
        }}
      >
        {children}
      </main>

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
};

export default AppLayout;
