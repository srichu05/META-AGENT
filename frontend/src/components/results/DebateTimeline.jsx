import React from 'react';
import { motion } from 'framer-motion';
import { AgentAvatar } from './AgentAvatar';
import { getAgentTheme } from '../../utils/agentTheme';
import { Trophy, Clock, Award, ShieldAlert } from 'lucide-react';
import Badge from '../common/Badge';

export const DebateTimeline = ({ debateHistory, winner, roundsCount }) => {
  if (!debateHistory || !Array.isArray(debateHistory.rounds) || debateHistory.rounds.length === 0) {
    return (
      <div
        style={{
          padding: '32px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          backgroundColor: 'var(--bg-subtle)',
          borderRadius: 'var(--radius-md)',
          border: '1px dashed var(--border-default)',
        }}
      >
        No multi-agent debate history recorded. Run a debate to view the chronological reasoning timeline.
      </div>
    );
  }

  const finalDecision = debateHistory.final_decision || {};

  return (
    <div style={{ position: 'relative', marginTop: '16px' }}>
      {/* Central Timeline Spine Line */}
      <div
        style={{
          position: 'absolute',
          left: '23px',
          top: '20px',
          bottom: '40px',
          width: '2px',
          backgroundColor: 'var(--border-default)',
          zIndex: 0,
        }}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', position: 'relative', zIndex: 1 }}>
        {debateHistory.rounds.map((roundItem, rIdx) => {
          const roundNum = roundItem.round || rIdx + 1;
          const timeStr = roundItem.timestamp
            ? new Date(roundItem.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            : null;

          return (
            <motion.div
              key={rIdx}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: rIdx * 0.1, duration: 0.3 }}
              style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
            >
              {/* Round Header Node */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '46px',
                    height: '46px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--bg-card)',
                    border: '2px solid var(--accent-cobalt)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 700,
                    fontSize: '0.875rem',
                    color: 'var(--accent-cobalt)',
                    boxShadow: 'var(--shadow-sm)',
                    flexShrink: 0,
                  }}
                >
                  R{roundNum}
                </div>
                <div>
                  <div
                    style={{
                      fontFamily: 'var(--font-display)',
                      fontWeight: 600,
                      fontSize: '1rem',
                      color: 'var(--text-primary)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span>Debate Round {roundNum}</span>
                    {timeStr && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--text-muted)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <Clock size={12} /> {timeStr}
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    Cross-examination and independent counter-theses
                  </div>
                </div>
              </div>

              {/* Agent Critique Cards within Round */}
              <div
                style={{
                  marginLeft: '46px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                {roundItem.critiques && typeof roundItem.critiques === 'object' && Object.keys(roundItem.critiques).length > 0 ? (
                  Object.entries(roundItem.critiques).map(([agentName, content], cIdx) => {
                    const theme = getAgentTheme(agentName);
                    const isError = typeof content === 'string' && content.toLowerCase().includes('error:');

                    return (
                      <div
                        key={cIdx}
                        style={{
                          backgroundColor: 'var(--bg-card)',
                          border: `1px solid ${theme.border}`,
                          borderLeft: `4px solid ${theme.accent}`,
                          borderRadius: 'var(--radius-md)',
                          padding: '16px 20px',
                          boxShadow: 'var(--shadow-sm)',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '10px',
                            gap: '8px',
                          }}
                        >
                          <AgentAvatar name={agentName} size="sm" showRole />
                          <div>
                            {isError ? (
                              <Badge variant="rose" size="sm" icon={ShieldAlert}>
                                Execution Flag
                              </Badge>
                            ) : (
                              <span
                                style={{
                                  fontSize: '0.75rem',
                                  fontFamily: 'var(--font-mono)',
                                  backgroundColor: theme.bg,
                                  color: theme.text,
                                  padding: '3px 8px',
                                  borderRadius: 'var(--radius-full)',
                                  fontWeight: 500,
                                }}
                              >
                                Turn Active
                              </span>
                            )}
                          </div>
                        </div>

                        <div
                          style={{
                            fontSize: '0.9rem',
                            color: 'var(--text-secondary)',
                            lineHeight: 1.6,
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'var(--font-body)',
                            backgroundColor: 'var(--bg-canvas)',
                            padding: '12px 14px',
                            borderRadius: 'var(--radius-sm)',
                            border: '1px solid var(--border-subtle)',
                          }}
                        >
                          {String(content)}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div
                    style={{
                      fontSize: '0.85rem',
                      color: 'var(--text-muted)',
                      fontStyle: 'italic',
                      padding: '12px',
                    }}
                  >
                    No agent dialogues in this round.
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}

        {/* Final Decision Node */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.3 }}
          style={{
            marginLeft: '20px',
            backgroundColor: 'var(--pastel-sage-bg)',
            border: '2px solid var(--pastel-sage-border)',
            borderRadius: 'var(--radius-lg)',
            padding: '24px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '14px',
              borderBottom: '1px solid var(--pastel-sage-border)',
              paddingBottom: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-card)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--pastel-sage-accent)',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <Trophy size={18} />
              </div>
              <div>
                <h4
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 700,
                    fontSize: '1.05rem',
                    color: 'var(--pastel-sage-text)',
                  }}
                >
                  Final Judicial Determination
                </h4>
                <div style={{ fontSize: '0.78rem', color: 'var(--pastel-sage-text)', opacity: 0.85 }}>
                  Consensus evaluation across all rounds
                </div>
              </div>
            </div>

            {winner && (
              <Badge variant="sage" size="md" icon={Award}>
                Winner: {winner}
              </Badge>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div
              style={{
                backgroundColor: 'var(--bg-card)',
                padding: '14px 18px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--pastel-sage-border)',
              }}
            >
              <div
                style={{
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  color: 'var(--pastel-sage-text)',
                  marginBottom: '4px',
                }}
              >
                Judge Reasoning
              </div>
              <p style={{ color: 'var(--text-primary)', fontSize: '0.925rem', lineHeight: 1.6 }}>
                {finalDecision.evaluation_reasoning || 'All agent proposals were reconciled into the final mathematical resolution.'}
              </p>
            </div>

            {typeof finalDecision.confidence === 'number' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.85rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--pastel-sage-text)', fontWeight: 600 }}>
                  Consensus Confidence:
                </span>
                <div
                  style={{
                    flex: 1,
                    maxWidth: '240px',
                    height: '8px',
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    borderRadius: 'var(--radius-full)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.round(finalDecision.confidence * 100)}%`,
                      backgroundColor: 'var(--pastel-sage-accent)',
                      borderRadius: 'var(--radius-full)',
                    }}
                  />
                </div>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--pastel-sage-text)' }}>
                  {(finalDecision.confidence * 100).toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default DebateTimeline;
