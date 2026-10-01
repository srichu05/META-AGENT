import React, { useState } from 'react';
import { parseMathSteps, sanitizeMathText } from '../../utils/mathFormatter';
import { Copy, Check, FileText } from 'lucide-react';

export const MathFormattedView = ({ solution = '', answer = '', title = 'Mathematical Derivation & Proof' }) => {
  const [copied, setCopied] = useState(false);

  if (!solution && !answer) {
    return (
      <div
        style={{
          padding: '24px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontStyle: 'italic',
        }}
      >
        No derivation steps generated yet.
      </div>
    );
  }

  const steps = parseMathSteps(solution || answer);

  const handleCopy = () => {
    const textToCopy = `${solution}\n\nFinal Answer: ${answer}`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Highlights mathematical tokens and equations inside a text line
  const renderHighlightedLine = (line, idx) => {
    // Check if line looks like an equation or mathematical computation (contains =, +, -, *, /, ^, or numbers)
    const isEquationLine = /(=|>|<|\\approx|\+|-|\*|\/)/.test(line) && /\d/.test(line);

    return (
      <div
        key={idx}
        style={{
          fontFamily: isEquationLine ? 'var(--font-mono)' : 'var(--font-body)',
          fontSize: isEquationLine ? '0.9rem' : '0.925rem',
          lineHeight: '1.6',
          color: isEquationLine ? '#1E293B' : 'var(--text-secondary)',
          backgroundColor: isEquationLine ? 'rgba(241, 245, 249, 0.6)' : 'transparent',
          padding: isEquationLine ? '4px 10px' : '2px 0',
          borderRadius: isEquationLine ? 'var(--radius-sm)' : '0',
          margin: isEquationLine ? '4px 0' : '2px 0',
          display: 'block',
          borderLeft: isEquationLine ? '2px solid var(--accent-cobalt-light)' : 'none',
        }}
      >
        {line}
      </div>
    );
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card-secondary)',
        border: '1px solid var(--border-default)',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          backgroundColor: 'var(--bg-subtle)',
          borderBottom: '1px solid var(--border-default)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={15} color="var(--accent-cobalt)" />
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.8rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--text-primary)',
            }}
          >
            {title}
          </span>
          <span
            style={{
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            ({steps.length} {steps.length === 1 ? 'Phase' : 'Phases'})
          </span>
        </div>

        <button
          onClick={handleCopy}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
          }}
          title="Copy solution text"
        >
          {copied ? (
            <>
              <Check size={12} color="var(--status-success)" />
              <span style={{ color: 'var(--status-success)' }}>Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Step by Step Breakdown */}
      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {steps.map((step, sIdx) => (
          <div
            key={sIdx}
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 18px',
              boxShadow: 'var(--shadow-sm)',
            }}
          >
            {step.title && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontFamily: 'var(--font-display)',
                  fontWeight: 600,
                  fontSize: '0.925rem',
                  color: 'var(--text-primary)',
                  marginBottom: '10px',
                  paddingBottom: '8px',
                  borderBottom: '1px dashed var(--border-subtle)',
                }}
              >
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--accent-cobalt-subtle)',
                    color: 'var(--accent-cobalt)',
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                  }}
                >
                  {sIdx + 1}
                </span>
                <span>{step.title}</span>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {step.content.map((line, lIdx) => renderHighlightedLine(line, lIdx))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MathFormattedView;
