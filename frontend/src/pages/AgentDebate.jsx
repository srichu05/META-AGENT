import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApp } from '../context/AppContext';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import AgentAvatar from '../components/results/AgentAvatar';
import MathFormattedView from '../components/results/MathFormattedView';
import DebateTimeline from '../components/results/DebateTimeline';
import {
  Gavel,
  MessageSquareCode,
  Trophy,
  RotateCcw,
  Sparkles,
  Users,
  Flame,
  CheckCircle2,
  ShieldAlert,
} from 'lucide-react';

export const AgentDebate = () => {
  const { addToast, executeDebate } = useApp();
  const [problemText, setProblemText] = useState(
    'A car travels at 60 mph for 2.5 hours. How far does the car travel, and would a 10% headwind affect distance if speed is kept constant?'
  );
  const [rounds, setRounds] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [debateResult, setDebateResult] = useState(null);

  const sampleDebateProblems = [
    {
      title: 'Counterexample Trap (Motion)',
      text: 'A car travels at 60 mph for 2.5 hours. How far does the car travel, and would a 10% headwind affect distance if speed is kept constant?',
    },
    {
      title: 'Boundary Geometry',
      text: 'A rectangular garden is 12 meters long and 8 meters wide. If a path 1 meter wide is built around the outside of the garden, what is the area of the path?',
    },
    {
      title: 'Fractional Remainder',
      text: 'Tom has 24 marbles. He gives 1/3 of them to his friend and 1/4 of the remaining marbles to his sister. How many marbles does Tom have left?',
    },
  ];

  const handleStartDebate = async () => {
    const trimmed = problemText.trim();
    if (!trimmed) {
      addToast('Please enter a problem for the agent debate arena', 'warning');
      return;
    }

    setIsLoading(true);

    try {
      const data = await executeDebate(trimmed, rounds);
      setDebateResult(data);
      addToast(`Debate completed across ${rounds} rounds!`, 'success');
    } catch (err) {
      console.error('Debate error:', err);
      addToast(err.message || 'Debate failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
      e.preventDefault();
      handleStartDebate();
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Configuration Card */}
      <Card
        title="Multi-Agent Automated Debate Arena"
        subtitle="Independent reasoning agents propose, critique, and cross-examine proofs under formal judicial evaluation."
        icon={MessageSquareCode}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Preset Prompts */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {sampleDebateProblems.map((p, idx) => (
              <button
                key={idx}
                onClick={() => setProblemText(p.text)}
                style={{
                  fontSize: '0.8rem',
                  fontFamily: 'var(--font-body)',
                  backgroundColor: 'var(--bg-subtle)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-full)',
                  padding: '4px 12px',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
              >
                {p.title}
              </button>
            ))}
          </div>

          {/* Problem Input Area */}
          <div>
            <textarea
              rows={4}
              value={problemText}
              onChange={(e) => setProblemText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter a problem that requires multi-perspective validation or counterexample checks..."
              style={{
                width: '100%',
                padding: '16px 18px',
                borderRadius: 'var(--radius-md)',
                border: '1.5px solid var(--border-default)',
                backgroundColor: 'var(--bg-card)',
                fontFamily: 'var(--font-body)',
                fontSize: '1rem',
                lineHeight: 1.6,
                color: 'var(--text-primary)',
                resize: 'vertical',
                boxShadow: 'inset 0 1px 2px rgba(15, 23, 42, 0.02)',
              }}
            />
          </div>

          {/* Configuration Controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            {/* Rounds Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label
                style={{
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  fontWeight: 600,
                }}
              >
                Debate Rounds:
              </label>
              <div style={{ display: 'flex', gap: '6px' }}>
                {[1, 2, 3, 4, 5].map((num) => (
                  <button
                    key={num}
                    onClick={() => setRounds(num)}
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: 'var(--radius-sm)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      border: rounds === num ? '2px solid var(--accent-cobalt)' : '1px solid var(--border-default)',
                      backgroundColor: rounds === num ? 'var(--accent-cobalt-subtle)' : 'var(--bg-card)',
                      color: rounds === num ? 'var(--accent-cobalt)' : 'var(--text-secondary)',
                      cursor: 'pointer',
                      transition: 'all var(--transition-fast)',
                    }}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>

            {/* Launch Action */}
            <Button
              variant="primary"
              size="lg"
              icon={Gavel}
              isLoading={isLoading}
              loadingText={`Convening Debate (${rounds} Rounds)...`}
              onClick={handleStartDebate}
              disabled={isLoading || !problemText.trim()}
            >
              Start Debate
            </Button>
          </div>
        </div>
      </Card>

      {/* Debate Results Area */}
      <AnimatePresence>
        {debateResult && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
          >
            {/* Top Winner & Rounds Summary Banner */}
            <div
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-default)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '20px',
                boxShadow: 'var(--shadow-card)',
              }}
            >
              <div>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  Debate Winner Award
                </span>
                <div style={{ marginTop: '8px' }}>
                  <AgentAvatar
                    name={debateResult.debate_winner || 'Proposer Agent (Alpha)'}
                    size="md"
                    showRole
                  />
                </div>
              </div>

              <div>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  Debate Iterations
                </span>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '1.85rem',
                    fontWeight: 700,
                    color: 'var(--accent-cobalt)',
                    marginTop: '4px',
                  }}
                >
                  {debateResult.debate_rounds || rounds} Rounds
                </div>
              </div>

              <div>
                <span
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  Consensus Status
                </span>
                <div style={{ marginTop: '8px' }}>
                  <Badge variant="sage" size="md" icon={CheckCircle2}>
                    Consensus Unanimous
                  </Badge>
                </div>
              </div>
            </div>

            {/* Final Solution Derivation */}
            <MathFormattedView
              solution={debateResult.final_solution}
              title="Consensus Final Solution & Theorem Derivation"
            />

            {/* Chronological Debate Timeline */}
            <Card
              title="Chronological Multi-Agent Debate Transcript"
              subtitle="Step-by-step cross-examination, proposals, and counter-criticisms across rounds."
              icon={Users}
            >
              <DebateTimeline
                debateHistory={debateResult.debate_history}
                winner={debateResult.debate_winner}
                roundsCount={debateResult.debate_rounds}
              />
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AgentDebate;
