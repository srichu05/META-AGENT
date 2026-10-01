import React from 'react';
import AppLayout from './components/layout/AppLayout';
import LandingPage from './pages/LandingPage';
import { useApp } from './context/AppContext';

export const App = () => {
  const { setActiveTab } = useApp();

  const handleNavigateSection = (sectionId) => {
    setActiveTab(sectionId);
    const workbench = document.getElementById('workbench-section');
    if (workbench) {
      workbench.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <AppLayout onNavigateSection={handleNavigateSection}>
      <LandingPage />
    </AppLayout>
  );
};

export default App;
