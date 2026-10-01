import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

export const Button = ({
  children,
  variant = 'primary', // 'primary' (solid white) | 'secondary' (dark border) | 'ghost' | 'pill' | 'danger'
  size = 'md', // 'sm' | 'md' | 'lg'
  isLoading = false,
  loadingText,
  icon: Icon,
  iconPosition = 'left',
  disabled = false,
  className = '',
  onClick,
  type = 'button',
  style = {},
  ...props
}) => {
  const getStyles = () => {
    const base = {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 600,
      fontFamily: 'var(--font-sans)',
      borderRadius: variant === 'pill' ? '9999px' : '8px',
      transition: 'all var(--transition-fast)',
      cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.45 : 1,
      gap: '8px',
      border: '1px solid transparent',
      textDecoration: 'none',
      letterSpacing: '-0.01em',
    };

    const sizePadding = {
      sm: { padding: '6px 12px', fontSize: '0.8125rem' },
      md: { padding: '9px 18px', fontSize: '0.875rem' },
      lg: { padding: '12px 24px', fontSize: '0.9375rem' },
    }[size] || { padding: '9px 18px', fontSize: '0.875rem' };

    const variants = {
      primary: {
        backgroundColor: '#FFFFFF',
        color: '#000000',
        borderColor: '#FFFFFF',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.3)',
      },
      pill: {
        backgroundColor: '#FFFFFF',
        color: '#000000',
        borderColor: '#FFFFFF',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.3)',
      },
      secondary: {
        backgroundColor: '#141414',
        color: '#FFFFFF',
        borderColor: 'rgba(255, 255, 255, 0.12)',
      },
      ghost: {
        backgroundColor: 'transparent',
        color: '#A1A1AA',
        borderColor: 'transparent',
      },
      danger: {
        backgroundColor: 'rgba(239, 68, 68, 0.12)',
        color: '#EF4444',
        borderColor: 'rgba(239, 68, 68, 0.25)',
      },
    }[variant] || {
      backgroundColor: '#FFFFFF',
      color: '#000000',
      borderColor: '#FFFFFF',
    };

    return { ...base, ...sizePadding, ...variants, ...style };
  };

  return (
    <motion.button
      type={type}
      style={getStyles()}
      whileHover={!disabled && !isLoading ? { opacity: 0.92, y: -1 } : {}}
      whileTap={!disabled && !isLoading ? { scale: 0.98 } : {}}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`ssych-button ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="animate-spin" size={size === 'sm' ? 14 : 16} />
          <span>{loadingText || children}</span>
        </>
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 14 : 16} />}
          <span>{children}</span>
          {Icon && iconPosition === 'right' && <Icon size={size === 'sm' ? 14 : 16} />}
        </>
      )}
    </motion.button>
  );
};

export default Button;
