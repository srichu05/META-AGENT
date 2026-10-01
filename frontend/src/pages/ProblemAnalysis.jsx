import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApp } from '../context/AppContext';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import {
  SearchCode,
  Lightbulb,
  Layers,
  Sparkles,
  HelpCircle,
  Compass,
  Zap,
  CheckCircle2,
  ChevronDown,
  Eye,
} from 'lucide-react';

export const ProblemAnalysis = () => {
  const { addToast, executeAnalyze } = useApp();
  const [problemText, setProblemText] = useState(
    'A store sells apples for ₹120 per kg. If John buys 5 kg of apples and pays with ₹1000, how much change will he receive?'
  );
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [revealedHints, setRevealedHints] = useState({});

  const sampleProblems = [
    'A store sells apples for ₹120 per kg. If John buys 5 kg of apples and pays with ₹1000, how much change will he receive?',
    'Find all integer solutions to the equation x^2 + 5y^2 = z^2.',
    'A cylindrical water tank of radius 3m and height 10m is being filled at a rate of 5 cubic meters per minute. How long will it take to fill 80% of the tank?',
  ];

  const handleAnalyze = async () => {
    const trimmed = problemText.trim();
    if (!trimmed) {
      addToast('Please enter a math problem to analyze', 'warning');
      return;
    }

    setIsLoading(true);

    try {
      const data = await executeAnalyze(trimmed);
      setAnalysisResult(data);
      setRevealedHints({ 0: true }); // reveal hint 1 by default
      addToast('Problem patterns successfully classified!', 'success');
    } catch (err) {
      console.error('Analyze error:', err);
      addToast(err.message || 'Analysis failed', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleHint = (idx) => {
    setRevealedHints((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Input Card */}
      <Card
        title="Analyze Problem Structure"
        subtitle="Classify algebraic patterns, difficulty rating, and extract tactical solution hints."
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Quick Benchmarks */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {sampleProblems.map((prob, idx) => (
              <button
                key={idx}
                onClick={() => setProblemText(prob)}
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
                Sample {idx + 1}
              </button>
            ))}
          </div>

          <textarea
            rows={3}
            value={problemText}
            onChange={(e) => setProblemText(e.target.value)}
            placeholder="Paste a mathematical problem to identify key concepts, difficulty, and algorithmic solution approaches..."
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

          <div>
            <Button
              variant="primary"
              size="lg"
              icon={Zap}
              isLoading={isLoading}
              loadingText="Analyzing Problem..."
              onClick={handleAnalyze}
              disabled={isLoading || !problemText.trim()}
            >
              Analyze Problem
            </Button>
          </div>
        </div>
      </Card>

      {/* Analysis Results Display */}
      <AnimatePresence>
        {analysisResult && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}
          >
            {/* Classification Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '18px',
              }}
            >
              {/* Domain */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '22px',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    marginBottom: '8px',
                  }}
                >
                  Mathematical Taxonomy
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontSize: '1.35rem',
                    fontWeight: 700,
                    color: 'var(--accent-cobalt)',
                    textTransform: 'capitalize',
                  }}
                >
                  {analysisResult.problem_type || 'Arithmetic Operations'}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                  Identified problem family
                </div>
              </div>

              {/* Difficulty Level */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '22px',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    marginBottom: '8px',
                  }}
                >
                  Complexity Gauge
                </div>
                <div>
                  <Badge variant="lemon" size="lg">
                    {analysisResult.difficulty || 'Intermediate (1400 ELO)'}
                  </Badge>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                  Reasoning depth assessment
                </div>
              </div>

              {/* Key Concepts */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '22px',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    marginBottom: '8px',
                  }}
                >
                  Core Mathematical Concepts
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.95rem',
                    color: 'var(--text-primary)',
                    fontWeight: 600,
                    lineHeight: 1.4,
                  }}
                >
                  {analysisResult.concepts || 'Unit Rates, Currency Invariants, Subtraction Axioms'}
                </div>
              </div>

              {/* Tactical Strategy */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '22px',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                    marginBottom: '8px',
                  }}
                >
                  Recommended Proof Strategy
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.925rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.4,
                  }}
                >
                  {analysisResult.approaches || 'Direct arithmetic substitution with RAG similarity alignment.'}
                </div>
              </div>
            </div>

            {/* Contextual Progressive Hints Section */}
            <Card
              title="Interactive Progressive Hints"
              subtitle="Scaffolded cues revealed on demand to guide mathematical derivation without giving away the full answer."
              icon={Lightbulb}
            >
              {analysisResult.hints && analysisResult.hints.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {analysisResult.hints.map((hint, hIdx) => {
                    const isRevealed = !!revealedHints[hIdx];

                    return (
                      <div
                        key={hIdx}
                        onClick={() => toggleHint(hIdx)}
                        style={{
                          backgroundColor: isRevealed ? 'var(--pastel-lemon-bg)' : 'var(--bg-subtle)',
                          border: `1px solid ${isRevealed ? 'var(--pastel-lemon-border)' : 'var(--border-default)'}`,
                          borderRadius: 'var(--radius-md)',
                          padding: '16px 20px',
                          display: 'flex',
                          alignItems: 'flex-start',
                          justifyContent: 'space-between',
                          gap: '14px',
                          cursor: 'pointer',
                          transition: 'all var(--transition-fast)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                          <span
                            style={{
                              width: '26px',
                              height: '26px',
                              borderRadius: '50%',
                              backgroundColor: 'var(--bg-card)',
                              color: isRevealed ? 'var(--pastel-lemon-text)' : 'var(--text-muted)',
                              border: `1px solid ${isRevealed ? 'var(--pastel-lemon-border)' : 'var(--border-default)'}`,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.75rem',
                              fontWeight: 700,
                              flexShrink: 0,
                              marginTop: '2px',
                            }}
                          >
                            {hIdx + 1}
                          </span>

                          <div>
                            <div
                              style={{
                                fontFamily: 'var(--font-mono)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                textTransform: 'uppercase',
                                color: isRevealed ? 'var(--pastel-lemon-text)' : 'var(--text-muted)',
                                marginBottom: '2px',
                              }}
                            >
                              Hint Stage {hIdx + 1}
                            </div>
                            <div
                              style={{
                                fontSize: '0.925rem',
                                color: isRevealed ? 'var(--pastel-lemon-text)' : 'var(--text-secondary)',
                                lineHeight: 1.55,
                                fontFamily: 'var(--font-body)',
                                filter: isRevealed ? 'none' : 'blur(4px)',
                                transition: 'filter 0.2s ease',
                                userSelect: isRevealed ? 'text' : 'none',
                              }}
                            >
                              {hint}
                            </div>
                          </div>
                        </div>

                        <div style={{ color: 'var(--text-muted)', marginTop: '4px', flexShrink: 0 }}>
                          {isRevealed ? <Eye size={16} /> : <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>[Click to reveal]</span>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No contextual hints required for this problem.
                </div>
              )}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ProblemAnalysis;
