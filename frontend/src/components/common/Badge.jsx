import React from 'react';

export const Badge = ({
  children,
  variant = 'default', // 'default' (#0E0E0E) | 'emerald' | 'cyan' | 'purple' | 'amber' | 'rose' | 'white'
  size = 'md', // 'sm' | 'md' | 'lg'
  icon: Icon,
  className = '',
  style = {},
  ...props
}) => {
  const sizeStyles = {
    sm: { padding: '3px 8px', fontSize: '0.7rem' },
    md: { padding: '4px 12px', fontSize: '0.75rem' },
    lg: { padding: '6px 16px', fontSize: '0.8125rem' },
  }[size] || { padding: '4px 12px', fontSize: '0.75rem' };

  const variantStyles = {
    default: {
      backgroundColor: '#0E0E0E',
      color: '#A1A1AA',
      borderColor: 'rgba(255, 255, 255, 0.12)',
    },
    emerald: {
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      color: '#10B981',
      borderColor: 'rgba(16, 185, 129, 0.25)',
    },
    cyan: {
      backgroundColor: 'rgba(6, 182, 212, 0.1)',
      color: '#06B6D4',
      borderColor: 'rgba(6, 182, 212, 0.25)',
    },
    purple: {
      backgroundColor: 'rgba(139, 92, 246, 0.1)',
      color: '#A78BFA',
      borderColor: 'rgba(139, 92, 246, 0.25)',
    },
    amber: {
      backgroundColor: 'rgba(245, 158, 11, 0.1)',
      color: '#FBBF24',
      borderColor: 'rgba(245, 158, 11, 0.25)',
    },
    rose: {
      backgroundColor: 'rgba(244, 63, 94, 0.1)',
      color: '#FB7185',
      borderColor: 'rgba(244, 63, 94, 0.25)',
    },
    white: {
      backgroundColor: '#FFFFFF',
      color: '#000000',
      borderColor: '#FFFFFF',
      fontWeight: 600,
    },
    // Backwards compatibility with previous variants
    sage: {
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      color: '#10B981',
      borderColor: 'rgba(16, 185, 129, 0.25)',
    },
    lavender: {
      backgroundColor: 'rgba(139, 92, 246, 0.1)',
      color: '#A78BFA',
      borderColor: 'rgba(139, 92, 246, 0.25)',
    },
    peach: {
      backgroundColor: 'rgba(249, 115, 22, 0.1)',
      color: '#FB923C',
      borderColor: 'rgba(249, 115, 22, 0.25)',
    },
    sky: {
      backgroundColor: 'rgba(56, 189, 248, 0.1)',
      color: '#38BDF8',
      borderColor: 'rgba(56, 189, 248, 0.25)',
    },
    neutral: {
      backgroundColor: '#0E0E0E',
      color: '#A1A1AA',
      borderColor: 'rgba(255, 255, 255, 0.12)',
    },
    dark: {
      backgroundColor: '#141414',
      color: '#FFFFFF',
      borderColor: 'rgba(255, 255, 255, 0.18)',
    },
  }[variant] || {
    backgroundColor: '#0E0E0E',
    color: '#A1A1AA',
    borderColor: 'rgba(255, 255, 255, 0.12)',
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        borderRadius: '9999px',
        borderWidth: '1px',
        borderStyle: 'solid',
        fontWeight: 500,
        fontFamily: 'var(--font-mono)',
        letterSpacing: '0.01em',
        transition: 'all var(--transition-fast)',
        ...sizeStyles,
        ...variantStyles,
        ...style,
      }}
      className={`ssych-badge ${className}`}
      {...props}
    >
      {Icon && <Icon size={size === 'sm' ? 11 : 13} />}
      {children}
    </span>
  );
};

export default Badge;
