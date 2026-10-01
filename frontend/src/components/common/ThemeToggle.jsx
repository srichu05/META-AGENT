import React from 'react';
import { motion } from 'framer-motion';
import { Sun, Moon } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const ThemeToggle = ({ size = 'md', showLabel = false }) => {
  const { theme, toggleTheme } = useApp();
  const isDark = theme === 'dark';

  return (
    <motion.button
      onClick={toggleTheme}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: size === 'sm' ? '5px 10px' : '6px 14px',
        borderRadius: 'var(--radius-full)',
        backgroundColor: 'var(--bg-subtle)',
        border: '1px solid var(--border-default)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-mono)',
        fontSize: size === 'sm' ? '0.75rem' : '0.8rem',
        fontWeight: 600,
        cursor: 'pointer',
        boxShadow: 'var(--shadow-subtle)',
        transition: 'all var(--transition-fast)',
      }}
      title={`Switch to ${isDark ? 'Light' : 'Dark'} Laboratory Theme`}
      aria-label="Toggle Theme Mode"
    >
      <motion.div
        key={theme}
        initial={{ rotate: -90, opacity: 0 }}
        animate={{ rotate: 0, opacity: 1 }}
        exit={{ rotate: 90, opacity: 0 }}
        transition={{ duration: 0.2 }}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: isDark ? '#FACC15' : '#D97706',
        }}
      >
        {isDark ? <Moon size={size === 'sm' ? 14 : 16} /> : <Sun size={size === 'sm' ? 14 : 16} />}
      </motion.div>

      {showLabel ? (
        <span>{isDark ? 'Dark Lab' : 'Light Lab'}</span>
      ) : (
        <span style={{ fontSize: '0.75rem', opacity: 0.85 }}>{isDark ? 'Dark' : 'Light'}</span>
      )}
    </motion.button>
  );
};

export default ThemeToggle;
