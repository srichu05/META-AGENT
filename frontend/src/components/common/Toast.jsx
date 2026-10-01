import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const ToastContainer = () => {
  const { toasts, removeToast } = useApp();

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        maxWidth: '420px',
        width: 'calc(100vw - 48px)',
        pointerEvents: 'none',
      }}
    >
      <AnimatePresence>
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
};

const ToastItem = ({ toast, onClose }) => {
  const icons = {
    success: <CheckCircle2 size={18} color="var(--status-success)" />,
    error: <XCircle size={18} color="var(--status-error)" />,
    warning: <AlertTriangle size={18} color="var(--status-warning)" />,
    info: <Info size={18} color="var(--accent-cobalt)" />,
  };

  const borderColors = {
    success: 'var(--status-success)',
    error: 'var(--status-error)',
    warning: 'var(--status-warning)',
    info: 'var(--accent-cobalt)',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      style={{
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-default)',
        borderLeft: `4px solid ${borderColors[toast.type] || borderColors.info}`,
        borderRadius: 'var(--radius-md)',
        padding: '12px 16px',
        boxShadow: 'var(--shadow-lg)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ marginTop: '2px', flexShrink: 0 }}>
        {icons[toast.type] || icons.info}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {toast.title && (
          <div
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '0.875rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '2px',
            }}
          >
            {toast.title}
          </div>
        )}
        <div
          style={{
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            wordBreak: 'break-word',
          }}
        >
          {toast.message}
        </div>
      </div>
      <button
        onClick={onClose}
        style={{
          color: 'var(--text-tertiary)',
          padding: '2px',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
        aria-label="Close"
      >
        <X size={15} />
      </button>
    </motion.div>
  );
};

export default ToastContainer;
