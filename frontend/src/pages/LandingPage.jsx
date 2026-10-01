import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useApp } from '../context/AppContext';
import ChromeEmblem from '../components/common/ChromeEmblem';
import InteractiveTerminal from '../components/landing/InteractiveTerminal';
import ProblemSolver from './ProblemSolver';
import AgentDebate from './AgentDebate';
import ProblemAnalysis from './ProblemAnalysis';
import SystemStats from './SystemStats';
import EvaluationMetrics from './EvaluationMetrics';
import KnowledgeCorpus from './KnowledgeCorpus';
import {
  ArrowRight,
  Calculator,
  MessageSquareCode,
  Sparkles,
  Database,
  Scale,
  Activity,
  Award,
  BookOpen,
  Cpu,
  Layers,
  ShieldCheck,
  ChevronDown,
  Plus,
  Minus,
  CheckCircle2,
  Terminal,
  ExternalLink,
} from 'lucide-react';

export const LandingPage = () => {
  const { activeTab, setActiveTab } = useApp();
  const [openFaq, setOpenFaq] = useState(null);

  // Categories matching Section 2 of ui.ssych.com
  const categories = [
    { id: 'solver', label: 'Problem Solver', icon: Calculator },
    { id: 'debate', label: 'Agent Debate', icon: MessageSquareCode },
    { id: 'analysis', label: 'Analysis', icon: Sparkles },
    { id: 'corpus', label: 'Vector RAG', icon: Database },
    { id: 'solver', label: 'Consensus', icon: Scale },
    { id: 'stats', label: 'Telemetry', icon: Activity },
    { id: 'evaluation', label: 'Evaluation', icon: Award },
    { id: 'corpus', label: 'Corpus', icon: BookOpen },
  ];

  // 6 Bento Features matching Section 4 of ui.ssych.com
  const bentoFeatures = [
    {
      icon: Cpu,
      title: 'Multi-Agent Synthesis',
      description:
        'Four specialized LLM agents—Solver, Verifier, Context, and Judge—collaborate dialectically to verify mathematical assertions.',
    },
    {
      icon: Database,
      title: 'Dense Vector RAG',
      description:
        'Retrieval-augmented grounding queries indexed GSM8K and theorem corpora with cosine similarity to extract axioms and proof lemmas.',
    },
    {
      icon: MessageSquareCode,
      title: 'Adversarial Debate Arena',
      description:
        'Multi-round cross-examination forces agents to challenge boundary conditions, expose arithmetic oversights, and establish consensus.',
    },
    {
      icon: Sparkles,
      title: 'Automated Taxonomy',
      description:
        'Instant problem classification categorizing difficulty levels, core mathematical disciplines, and generating tactical hints.',
    },
    {
      icon: Activity,
      title: 'Real-Time Telemetry',
      description:
        'Microsecond latency tracking, model confidence scores, memory vector allocation, and system execution telemetry.',
    },
    {
      icon: ShieldCheck,
      title: 'Formal Step Verification',
      description:
        'Strict step-by-step invariant verification guaranteeing intermediate algebraic transformations hold before final conclusion.',
    },
  ];

  // Screen Tabs for Section 6 ("Whole screens, not just parts")
  const screenTabs = [
    { id: 'solver', label: 'Problem Solver' },
    { id: 'debate', label: 'Agent Debate Arena' },
    { id: 'analysis', label: 'Problem Taxonomy & Analysis' },
    { id: 'stats', label: 'System Statistics & Telemetry' },
    { id: 'evaluation', label: 'Evaluation Benchmarks' },
    { id: 'corpus', label: 'Knowledge Corpus Manager' },
  ];

  // FAQ Items matching Section 7 of ui.ssych.com
  const faqList = [
    {
      q: 'How does the multi-agent consensus system eliminate mathematical hallucinations?',
      a: 'Instead of relying on a single generative pass, META-AGENT separates problem solving into dedicated roles: a Proposer, an Adversarial Critic who attacks candidate derivations, a Context Retriever supplying ground truth lemmas, and an impartial Consensus Judge that requires strict mathematical proof before declaring a solution verified.',
    },
    {
      q: 'What benchmark datasets power the vector RAG retrieval?',
      a: 'The system indexes the GSM8K benchmark corpus alongside curated competition mathematics problems. High-dimensional vector embeddings are stored locally with cosine similarity indexing, allowing fast retrieval of analogous problem structures and verified lemma steps.',
    },
    {
      q: 'How are debate rounds scored by the Consensus Judge?',
      a: 'In each debate round, agents critique opposing steps, identify arithmetic or conceptual errors, and propose counterexamples. The Consensus Judge evaluates both arguments against formal axioms, calculates an overall confidence score, and determines the winning derivation.',
    },
    {
      q: 'Can custom JSON/JSONL datasets be ingested dynamically?',
      a: 'Yes. The Knowledge Corpus manager accepts standard JSON and JSONL problem collections with drag-and-drop support, automatically parsing question/answer pairs and indexing them into the vector database in real time.',
    },
    {
      q: 'Does the application work offline or without an active Flask kernel?',
      a: 'Yes. META-AGENT features an intelligent dual-mode architecture: when connected to the Flask backend (port 5000), it executes live model inferences; when offline, it seamlessly transitions into a realistic demonstration mode with full interactive workflows.',
    },
  ];

  const scrollToWorkbench = (tabId) => {
    if (tabId) setActiveTab(tabId);
    const el = document.getElementById('workbench-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const scrollToTerminal = () => {
    const el = document.getElementById('terminal-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const renderActiveScreen = () => {
    switch (activeTab) {
      case 'solver':
        return <ProblemSolver key="solver-screen" />;
      case 'debate':
        return <AgentDebate key="debate-screen" />;
      case 'analysis':
        return <ProblemAnalysis key="analysis-screen" />;
      case 'stats':
        return <SystemStats key="stats-screen" />;
      case 'evaluation':
        return <EvaluationMetrics key="evaluation-screen" />;
      case 'corpus':
        return <KnowledgeCorpus key="corpus-screen" />;
      default:
        return <ProblemSolver key="default-screen" />;
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', overflowX: 'hidden' }}>
      {/* Top Ambient Vignette */}
      <div className="ssych-canvas-vignette" />

      {/* ====================================================================
          SECTION 1: HERO SECTION (Exact replication of ui.ssych.com hero)
          ==================================================================== */}
      <section
        style={{
          paddingTop: '72px',
          paddingBottom: '80px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div className="ssych-container">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 0.95fr)',
              gap: '48px',
              alignItems: 'center',
            }}
          >
            {/* Left Content Column */}
            <div>
              {/* Badge Pill */}
              <div style={{ marginBottom: '24px' }}>
                <a
                  href="#terminal-section"
                  onClick={(e) => {
                    e.preventDefault();
                    scrollToTerminal();
                  }}
                  className="ssych-pill-badge"
                >
                  <span>4-Agent Consensus Engine, RAG Enabled</span>
                  <span style={{ color: '#71717A' }}>&gt;</span>
                </a>
              </div>

              {/* Exact Split Headline */}
              <h1 className="ssych-headline-split" style={{ marginBottom: '24px' }}>
                <span className="primary">Reasoning for</span>
                <span className="muted">high-stakes</span>
                <span className="muted">mathematics</span>
              </h1>

              {/* Body Text */}
              <p
                style={{
                  fontSize: '1.0625rem',
                  lineHeight: 1.6,
                  color: '#A1A1AA',
                  maxWidth: '520px',
                  marginBottom: '36px',
                }}
              >
                Multi-agent mathematical reasoning platform for surfaces where being wrong is expensive.
                Every derivation is cross-verified, every lemma is RAG-retrieved, and every step is audited.
              </p>

              {/* Actions Row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
                <button onClick={scrollToTerminal} className="ssych-btn-white">
                  <span>Solve Problem</span>
                  <ArrowRight size={15} strokeWidth={2.5} />
                </button>

                <button
                  onClick={() => scrollToWorkbench('debate')}
                  className="ssych-btn-ghost"
                >
                  <span>Automated Debate</span>
                  <span style={{ color: '#71717A' }}>&gt;</span>
                </button>
              </div>
            </div>

            {/* Right Graphic: 3D Chrome Emblem */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                position: 'relative',
              }}
            >
              <ChromeEmblem size={360} />
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 2: CATEGORY ICON ROW ("Everything mathematical reasoning demands")
          ==================================================================== */}
      <section style={{ padding: '64px 0 32px 0', position: 'relative', zIndex: 1 }}>
        <div className="ssych-container">
          <div style={{ textAlign: 'center', marginBottom: '40px' }}>
            <h2 className="ssych-section-heading">
              <span className="primary">Everything mathematical reasoning </span>
              <span className="muted">demands</span>
            </h2>
          </div>

          {/* Categories Grid */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
              flexWrap: 'wrap',
            }}
          >
            {categories.map((cat, idx) => {
              const Icon = cat.icon;
              const isSelected = activeTab === cat.id;
              return (
                <button
                  key={idx}
                  onClick={() => scrollToWorkbench(cat.id)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '12px 14px',
                    borderRadius: '12px',
                    backgroundColor: isSelected ? '#141414' : 'transparent',
                    transition: 'all var(--transition-fast)',
                    cursor: 'pointer',
                    minWidth: '92px',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#121212';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = isSelected ? '#141414' : 'transparent';
                  }}
                >
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '10px',
                      backgroundColor: '#121212',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: isSelected ? '#FFFFFF' : '#A1A1AA',
                      boxShadow: isSelected ? '0 0 16px rgba(255, 255, 255, 0.1)' : 'none',
                    }}
                  >
                    <Icon size={20} />
                  </div>
                  <span
                    style={{
                      fontSize: '0.785rem',
                      fontWeight: 500,
                      color: isSelected ? '#FFFFFF' : '#71717A',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {cat.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 3: INTERACTIVE TERMINAL / SOLVER WORKBENCH (Section 3 of reference)
          ==================================================================== */}
      <section
        id="terminal-section"
        style={{
          padding: '36px 0 80px 0',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div className="ssych-container">
          <InteractiveTerminal />
        </div>
      </section>

      {/* ====================================================================
          SECTION 4: 6-CARD BENTO FEATURE GRID ("Architected for rigor where accuracy matters")
          ==================================================================== */}
      <section style={{ padding: '80px 0', position: 'relative', zIndex: 1 }}>
        <div className="ssych-container">
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <h2 className="ssych-section-heading">
              <span className="primary">Architected for rigor </span>
              <span className="muted">where accuracy matters</span>
            </h2>
          </div>

          {/* 3 x 2 Bento Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '20px',
            }}
          >
            {bentoFeatures.map((feat, idx) => {
              const Icon = feat.icon;
              return (
                <div
                  key={idx}
                  className="ssych-card"
                  style={{
                    backgroundColor: '#0C0C0C',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '14px',
                    padding: '28px',
                    display: 'flex',
                    flexDirection: 'column',
                  }}
                >
                  <div className="ssych-icon-box">
                    <Icon size={20} />
                  </div>
                  <h3
                    style={{
                      fontSize: '1.0625rem',
                      fontWeight: 600,
                      color: '#FFFFFF',
                      marginBottom: '10px',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {feat.title}
                  </h3>
                  <p
                    style={{
                      fontSize: '0.875rem',
                      color: '#71717A',
                      lineHeight: 1.6,
                    }}
                  >
                    {feat.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 5: KPI STATS BANNER (4-Stat Card matching Section 5)
          ==================================================================== */}
      <section style={{ padding: '32px 0 72px 0', position: 'relative', zIndex: 1 }}>
        <div className="ssych-container">
          <div
            style={{
              backgroundColor: '#0C0C0C',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '16px',
              padding: '36px 24px',
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: '24px',
              textAlign: 'center',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: '2.5rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-sans)',
                  color: '#FFFFFF',
                  letterSpacing: '-0.03em',
                  lineHeight: 1.1,
                }}
              >
                4
              </div>
              <div style={{ fontSize: '0.84rem', color: '#71717A', marginTop: '6px' }}>
                specialized reasoning agents
              </div>
            </div>

            <div>
              <div
                style={{
                  fontSize: '2.5rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-sans)',
                  color: '#FFFFFF',
                  letterSpacing: '-0.03em',
                  lineHeight: 1.1,
                }}
              >
                7,473
              </div>
              <div style={{ fontSize: '0.84rem', color: '#71717A', marginTop: '6px' }}>
                GSM8K benchmark problems
              </div>
            </div>

            <div>
              <div
                style={{
                  fontSize: '2.5rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-sans)',
                  color: '#FFFFFF',
                  letterSpacing: '-0.03em',
                  lineHeight: 1.1,
                }}
              >
                94.2%
              </div>
              <div style={{ fontSize: '0.84rem', color: '#71717A', marginTop: '6px' }}>
                consensus verification accuracy
              </div>
            </div>

            <div>
              <div
                style={{
                  fontSize: '2.5rem',
                  fontWeight: 700,
                  fontFamily: 'var(--font-sans)',
                  color: '#FFFFFF',
                  letterSpacing: '-0.03em',
                  lineHeight: 1.1,
                }}
              >
                &lt; 1.2s
              </div>
              <div style={{ fontSize: '0.84rem', color: '#71717A', marginTop: '6px' }}>
                mean synthesis latency
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 6: "WHOLE SCREENS, NOT JUST PARTS" (The Live Operational Frame)
          ==================================================================== */}
      <section
        id="workbench-section"
        style={{
          padding: '80px 0',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div className="ssych-container">
          <div style={{ textAlign: 'center', marginBottom: '32px' }}>
            <h2 className="ssych-section-heading" style={{ marginBottom: '12px' }}>
              <span className="primary">Whole screens, </span>
              <span className="muted">not just parts</span>
            </h2>
            <p style={{ fontSize: '0.9375rem', color: '#71717A' }}>
              Switch between complete operational surfaces to solve, debate, analyze, and inspect the system.
            </p>
          </div>

          {/* Interactive Screen Tab Pills */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              flexWrap: 'wrap',
              marginBottom: '32px',
            }}
          >
            {screenTabs.map((tab) => {
              const isSelected = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '8px 18px',
                    borderRadius: '9999px',
                    fontSize: '0.84rem',
                    fontWeight: 500,
                    backgroundColor: isSelected ? '#1A1A1A' : 'transparent',
                    color: isSelected ? '#FFFFFF' : '#71717A',
                    border: isSelected ? '1px solid rgba(255, 255, 255, 0.18)' : '1px solid transparent',
                    transition: 'all var(--transition-fast)',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.color = '#FFFFFF';
                      e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.04)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.color = '#71717A';
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Master Application Window Frame */}
          <div
            style={{
              backgroundColor: '#090909',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflow: 'hidden',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.8)',
            }}
          >
            {/* Window Chrome Header */}
            <div
              style={{
                backgroundColor: '#0E0E0E',
                borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
                padding: '12px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#262626' }} />
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#262626' }} />
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#262626' }} />
                <span
                  style={{
                    fontSize: '0.785rem',
                    color: '#71717A',
                    fontFamily: 'var(--font-mono)',
                    marginLeft: '12px',
                  }}
                >
                  meta-agent // {activeTab}.module
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    color: '#10B981',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  LIVE KERNEL
                </span>
              </div>
            </div>

            {/* Active Screen Surface */}
            <div style={{ padding: '28px' }}>
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.2 }}
                >
                  {renderActiveScreen()}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 7: FAQ ACCORDION ("Questions, answered")
          ==================================================================== */}
      <section style={{ padding: '80px 0', position: 'relative', zIndex: 1 }}>
        <div className="ssych-container" style={{ maxWidth: '840px' }}>
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <h2 className="ssych-section-heading">
              <span className="primary">Questions, </span>
              <span className="muted">answered</span>
            </h2>
          </div>

          {/* Accordion List */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {faqList.map((item, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div
                  key={idx}
                  style={{
                    borderTop: '1px solid rgba(255, 255, 255, 0.08)',
                    padding: '24px 0',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  <button
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      textAlign: 'left',
                      color: isOpen ? '#FFFFFF' : '#E4E4E7',
                      fontSize: '1.0625rem',
                      fontWeight: 500,
                      gap: '16px',
                    }}
                  >
                    <span>{item.q}</span>
                    <span
                      style={{
                        color: '#71717A',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {isOpen ? <Minus size={18} /> : <Plus size={18} />}
                    </span>
                  </button>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        style={{ overflow: 'hidden' }}
                      >
                        <p
                          style={{
                            marginTop: '14px',
                            fontSize: '0.9375rem',
                            color: '#71717A',
                            lineHeight: 1.65,
                          }}
                        >
                          {item.a}
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)' }} />
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 8: PRE-FOOTER CTA BANNER ("Reason through complex problems with certainty")
          ==================================================================== */}
      <section style={{ padding: '80px 0 100px 0', position: 'relative', zIndex: 1 }}>
        <div className="ssych-container">
          <div style={{ textAlign: 'center', maxWidth: '720px', margin: '0 auto' }}>
            <h2
              className="ssych-headline-split"
              style={{
                fontSize: 'clamp(2.2rem, 4.5vw, 3.5rem)',
                marginBottom: '32px',
              }}
            >
              <span className="primary">Reason through complex problems </span>
              <span className="muted">with certainty</span>
            </h2>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
              <button onClick={scrollToTerminal} className="ssych-btn-white">
                <span>Solve Problem Now</span>
                <ArrowRight size={15} strokeWidth={2.5} />
              </button>

              <button
                onClick={() => scrollToWorkbench('debate')}
                className="ssych-btn-ghost"
              >
                <span>Explore Debate Arena</span>
                <span style={{ color: '#71717A' }}>&gt;</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ====================================================================
          SECTION 9: MINIMALIST DARK FOOTER (Exact structure of ui.ssych.com footer)
          ==================================================================== */}
      <footer
        style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          backgroundColor: '#050505',
          padding: '64px 0 48px 0',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div className="ssych-container">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1.4fr) repeat(3, minmax(0, 1fr))',
              gap: '48px',
              marginBottom: '48px',
            }}
          >
            {/* Col 1: Brand & Desc */}
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  marginBottom: '14px',
                }}
              >
                <div
                  style={{
                    width: '24px',
                    height: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <svg width="20" height="20" viewBox="0 0 28 28" fill="none">
                    <path d="M4 8L14 3L24 8L14 13L4 8Z" fill="#FFFFFF" />
                    <path d="M4 14L14 19L24 14L14 9L4 14Z" fill="#94A3B8" />
                    <path d="M4 20L14 25L24 20L14 15L4 20Z" fill="#475569" />
                  </svg>
                </div>
                <span
                  style={{
                    fontFamily: 'var(--font-sans)',
                    fontSize: '1rem',
                    fontWeight: 700,
                    letterSpacing: '-0.025em',
                    color: '#FFFFFF',
                  }}
                >
                  META-AGENT
                </span>
              </div>
              <p style={{ fontSize: '0.84rem', color: '#71717A', lineHeight: 1.6, maxWidth: '280px' }}>
                Multi-Agent Mathematical Reasoning and Automated Dialectical Debate Engine.
              </p>
            </div>

            {/* Col 2: Product */}
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  color: '#71717A',
                  marginBottom: '16px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                INTELLIGENCE
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('solver')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Problem Solver
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('debate')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Agent Debate Arena
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('analysis')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Problem Analysis
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('corpus')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Vector RAG Database
                </a>
              </div>
            </div>

            {/* Col 3: Benchmarks */}
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  color: '#71717A',
                  marginBottom: '16px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                BENCHMARKS
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('evaluation')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  GSM8K Benchmark
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('stats')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Hardware Telemetry
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('corpus')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Lemma Corpus
                </a>
                <a
                  href="#workbench-section"
                  onClick={() => scrollToWorkbench('evaluation')}
                  style={{ fontSize: '0.875rem', color: '#A1A1AA', textDecoration: 'none' }}
                >
                  Confidence Metrics
                </a>
              </div>
            </div>

            {/* Col 4: Kernel */}
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  color: '#71717A',
                  marginBottom: '16px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                SYSTEM
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <span style={{ fontSize: '0.875rem', color: '#71717A' }}>Flask API Kernel (5000)</span>
                <span style={{ fontSize: '0.875rem', color: '#71717A' }}>Vite React Frontend (5173)</span>
                <span style={{ fontSize: '0.875rem', color: '#71717A' }}>Dialectical Consensus Engine</span>
                <span style={{ fontSize: '0.875rem', color: '#71717A' }}>SQLite & Vector Store</span>
              </div>
            </div>
          </div>

          {/* Bottom Copyright & Status */}
          <div
            style={{
              paddingTop: '24px',
              borderTop: '1px solid rgba(255, 255, 255, 0.05)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.785rem',
              color: '#52525B',
              fontFamily: 'var(--font-mono)',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div>© {new Date().getFullYear()} META-AGENT. Recreated faithfully from ui.ssych.com reference.</div>
            <div>Multi-Agent Consensus & Formal Verification</div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
