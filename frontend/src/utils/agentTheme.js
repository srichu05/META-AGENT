// Palette mapping for Agent roles, personas, and pastel styling

export const AGENT_THEMES = {
  meta: {
    name: 'Meta-Agent Orchestrator',
    role: 'Synthesizer & Consensus',
    bg: 'var(--pastel-lavender-bg)',
    border: 'var(--pastel-lavender-border)',
    text: 'var(--pastel-lavender-text)',
    accent: 'var(--pastel-lavender-accent)',
    badgeClass: 'badge-lavender',
    symbol: 'Ψ'
  },
  judge: {
    name: 'Judge Verifier',
    role: 'Formal Evaluator & Arbiter',
    bg: 'var(--pastel-sage-bg)',
    border: 'var(--pastel-sage-border)',
    text: 'var(--pastel-sage-text)',
    accent: 'var(--pastel-sage-accent)',
    badgeClass: 'badge-sage',
    symbol: '⚖'
  },
  proposer: {
    name: 'Proposer Agent (Alpha)',
    role: 'Hypothesis & Direct Derivation',
    bg: 'var(--pastel-peach-bg)',
    border: 'var(--pastel-peach-border)',
    text: 'var(--pastel-peach-text)',
    accent: 'var(--pastel-peach-accent)',
    badgeClass: 'badge-peach',
    symbol: 'α'
  },
  critic: {
    name: 'Counterexample Critic (Beta)',
    role: 'Refutation & Edge Cases',
    bg: 'var(--pastel-rose-bg)',
    border: 'var(--pastel-rose-border)',
    text: 'var(--pastel-rose-text)',
    accent: 'var(--pastel-rose-accent)',
    badgeClass: 'badge-rose',
    symbol: 'β'
  },
  retriever: {
    name: 'RAG Retriever Agent',
    role: 'Corpus Knowledge & Lemmas',
    bg: 'var(--pastel-lemon-bg)',
    border: 'var(--pastel-lemon-border)',
    text: 'var(--pastel-lemon-text)',
    accent: 'var(--pastel-lemon-accent)',
    badgeClass: 'badge-lemon',
    symbol: '∇'
  },
  solver: {
    name: 'Formal Math Solver',
    role: 'Algebraic & Arithmetic Solver',
    bg: 'var(--pastel-sky-bg)',
    border: 'var(--pastel-sky-border)',
    text: 'var(--pastel-sky-text)',
    accent: 'var(--pastel-sky-accent)',
    badgeClass: 'badge-sky',
    symbol: '∑'
  },
  default: {
    name: 'Research Agent',
    role: 'Reasoning Unit',
    bg: '#F3F4F6',
    border: '#E5E7EB',
    text: '#374151',
    accent: '#6B7280',
    badgeClass: 'badge-neutral',
    symbol: 'λ'
  }
};

export const getAgentTheme = (agentName = '') => {
  if (!agentName) return AGENT_THEMES.default;
  const lower = agentName.toLowerCase();

  if (lower.includes('judge') || lower.includes('arbiter') || lower.includes('verifier')) {
    return AGENT_THEMES.judge;
  }
  if (lower.includes('meta') || lower.includes('orchestrator') || lower.includes('synthesizer')) {
    return AGENT_THEMES.meta;
  }
  if (lower.includes('critic') || lower.includes('counter') || lower.includes('refut') || lower.includes('adversar')) {
    return AGENT_THEMES.critic;
  }
  if (lower.includes('propos') || lower.includes('alpha') || lower.includes('direct') || lower.includes('groq')) {
    return AGENT_THEMES.proposer;
  }
  if (lower.includes('retriev') || lower.includes('rag') || lower.includes('corpus')) {
    return AGENT_THEMES.retriever;
  }
  if (lower.includes('solver') || lower.includes('math') || lower.includes('beta')) {
    return AGENT_THEMES.solver;
  }

  // Hash-based deterministic fallback from pastel options
  const keys = ['proposer', 'critic', 'solver', 'meta', 'judge', 'retriever'];
  let hash = 0;
  for (let i = 0; i < agentName.length; i++) {
    hash = (hash << 5) - hash + agentName.charCodeAt(i);
    hash |= 0;
  }
  const key = keys[Math.abs(hash) % keys.length];
  return AGENT_THEMES[key] || AGENT_THEMES.default;
};
