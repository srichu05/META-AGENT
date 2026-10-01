import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import {
  MOCK_SOLVE_RESULT,
  MOCK_DEBATE_RESULT,
  MOCK_ANALYZE_RESULT,
  MOCK_STATS_RESULT,
  MOCK_EVALUATION_RESULT,
  MOCK_CORPUS_DATA,
} from '../utils/mockData';

const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [activeTab, setActiveTab] = useState('solver');
  const [backendStatus, setBackendStatus] = useState('connecting'); // 'connected' | 'connecting' | 'disconnected'
  const [healthInfo, setHealthInfo] = useState(null);
  const [sampleProblems, setSampleProblems] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Theme Mode: Obsidian Dark strictly matching ui.ssych.com reference
  const [theme, setTheme] = useState('dark');

  const toggleTheme = useCallback(() => {
    // Pure obsidian design specification
  }, []);

  useEffect(() => {
    localStorage.setItem('meta_agent_theme', 'dark');
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  // Add toast notification (debounced to avoid duplicate flood)
  const addToast = useCallback((message, type = 'info', title = '') => {
    const id = Date.now() + Math.random().toString(36).substring(2, 7);
    setToasts((prev) => {
      if (prev.some((t) => t.message === message)) return prev;
      return [...prev, { id, message, type, title }];
    });

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Health check function with graceful fallback
  const checkBackendHealth = useCallback(async () => {
    try {
      setBackendStatus((prev) => (prev === 'connected' ? 'connected' : 'connecting'));
      const res = await api.checkHealth();
      setHealthInfo(res);
      setBackendStatus('connected');
      setIsDemoMode(false);
    } catch (err) {
      setBackendStatus('disconnected');
      setIsDemoMode(true);
    }
  }, []);

  // Load benchmark problems
  const loadSampleProblems = useCallback(async () => {
    try {
      const res = await api.getSampleProblems();
      const list = res?.problems || res || [];
      if (Array.isArray(list) && list.length > 0) {
        const normalized = list
          .map((item) => (typeof item === 'string' ? item : item.problem || item.question || ''))
          .filter(Boolean);
        if (normalized.length > 0) {
          setSampleProblems(normalized);
          return;
        }
      }
    } catch (err) {
      // fallback
    }
    setSampleProblems(MOCK_CORPUS_DATA.map((p) => p.problem));
  }, []);

  // Hybrid dispatchers that seamlessly switch between live backend and realistic simulation
  const executeSolve = async (problem) => {
    if (backendStatus === 'connected') {
      return await api.solveProblem(problem);
    }
    await new Promise((r) => setTimeout(r, 1400));
    return {
      ...MOCK_SOLVE_RESULT,
      problem,
    };
  };

  const executeDebate = async (problem, rounds) => {
    if (backendStatus === 'connected') {
      return await api.runDebate(problem, rounds);
    }
    await new Promise((r) => setTimeout(r, 2000));
    return {
      ...MOCK_DEBATE_RESULT,
      debate_rounds: rounds,
    };
  };

  const executeAnalyze = async (problem) => {
    if (backendStatus === 'connected') {
      return await api.analyzeProblem(problem);
    }
    await new Promise((r) => setTimeout(r, 900));
    return {
      ...MOCK_ANALYZE_RESULT,
      problem,
    };
  };

  const executeGetStats = async () => {
    if (backendStatus === 'connected') {
      return await api.getSystemStats();
    }
    await new Promise((r) => setTimeout(r, 400));
    return MOCK_STATS_RESULT;
  };

  const executeGetEvaluation = async () => {
    if (backendStatus === 'connected') {
      return await api.getLastEvaluation();
    }
    await new Promise((r) => setTimeout(r, 400));
    return {
      success: true,
      evaluation: MOCK_EVALUATION_RESULT,
    };
  };

  const executeGetCorpus = async () => {
    if (backendStatus === 'connected') {
      return await api.getCorpus();
    }
    await new Promise((r) => setTimeout(r, 500));
    return {
      success: true,
      count: MOCK_CORPUS_DATA.length,
      problems: MOCK_CORPUS_DATA,
    };
  };

  const executeUploadCorpus = async (file, onProgress) => {
    if (backendStatus === 'connected') {
      return await api.uploadCorpus(file, onProgress);
    }
    for (let i = 10; i <= 100; i += 20) {
      if (onProgress) onProgress({ loaded: i, total: 100 });
      await new Promise((r) => setTimeout(r, 150));
    }
    return {
      success: true,
      message: `Indexed "${file.name}" with 120 vector embeddings into RAG database.`,
      count: 120,
    };
  };

  // Poll health status
  useEffect(() => {
    checkBackendHealth();
    loadSampleProblems();

    const interval = setInterval(() => {
      checkBackendHealth();
    }, 12000);

    return () => clearInterval(interval);
  }, [checkBackendHealth, loadSampleProblems]);

  return (
    <AppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        backendStatus,
        healthInfo,
        checkBackendHealth,
        isDemoMode,
        setIsDemoMode,
        theme,
        toggleTheme,
        sampleProblems,
        loadSampleProblems,
        toasts,
        addToast,
        removeToast,
        isSidebarCollapsed,
        setIsSidebarCollapsed,
        // High-level operations
        executeSolve,
        executeDebate,
        executeAnalyze,
        executeGetStats,
        executeGetEvaluation,
        executeGetCorpus,
        executeUploadCorpus,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

export default AppContext;
