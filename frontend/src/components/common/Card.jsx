import React from 'react';
import { motion } from 'framer-motion';

export const Card = ({
  children,
  title,
  subtitle,
  icon: Icon,
  badge,
  actions,
  variant = 'default', // 'default' (#0C0C0C) | 'secondary' (#0E0E0E) | 'inner' (#090909)
  className = '',
  style = {},
  animate = true,
  onClick,
  ...props
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'secondary':
        return {
          backgroundColor: '#0E0E0E',
          borderColor: 'rgba(255, 255, 255, 0.08)',
        };
      case 'inner':
        return {
          backgroundColor: '#090909',
          borderColor: 'rgba(255, 255, 255, 0.08)',
        };
      default:
        return {
          backgroundColor: '#0C0C0C',
          borderColor: 'rgba(255, 255, 255, 0.08)',
        };
    }
  };

  const Component = animate ? motion.div : 'div';
  const motionProps = animate
    ? {
        initial: { opacity: 0, y: 6 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
      }
    : {};

  return (
    <Component
      style={{
        borderRadius: '14px',
        borderWidth: '1px',
        borderStyle: 'solid',
        padding: '24px',
        color: '#FFFFFF',
        transition: 'border-color var(--transition-fast), transform var(--transition-fast)',
        ...getVariantStyles(),
        ...style,
      }}
      className={`ssych-card ${className}`}
      onClick={onClick}
      {...motionProps}
      {...props}
    >
      {(title || subtitle || Icon || badge || actions) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            marginBottom: '18px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            paddingBottom: '14px',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {Icon && (
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  backgroundColor: '#141414',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  flexShrink: 0,
                }}
              >
                <Icon size={18} />
              </div>
            )}
            <div>
              {title && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h3
                    style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: '#FFFFFF',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {title}
                  </h3>
                  {badge}
                </div>
              )}
              {subtitle && (
                <p
                  style={{
                    fontSize: '0.8125rem',
                    color: '#71717A',
                    marginTop: '2px',
                  }}
                >
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {actions && <div style={{ display: 'flex', gap: '8px' }}>{actions}</div>}
        </div>
      )}
      {children}
    </Component>
  );
};

export default Card;
