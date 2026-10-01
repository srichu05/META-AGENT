// Utilities for mathematical text sanitization, step segmentation, and LaTeX-style rendering

export const sanitizeMathText = (text) => {
  if (!text) return '';
  let cleaned = String(text);

  // 1. Remove raw token artifacts like [*] or (*) or <think> tags
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/gi, '');
  cleaned = cleaned.replace(/[\[\*\]]|\(\*\)/g, '');
  // 2. Strip HTML tags that might leak from markdown
  cleaned = cleaned.replace(/<[^>]*>/g, '');
  // 3. Remove escaped HTML fragments like ="number"> or ="operator">
  cleaned = cleaned.replace(/=\s*"[^"]*"\s*>/g, '');
  // 4. Remove HTML entities
  cleaned = cleaned.replace(/&#\d+;|&#[A-Za-z]+;/g, '');
  // 5. Clean markdown asterisks
  cleaned = cleaned.replace(/\*\*(.*?)\*\*/g, '$1');
  cleaned = cleaned.replace(/\*(.*?)\*/g, '$1');
  // 6. Remove leading bullet symbols
  cleaned = cleaned.replace(/^\s*[\*-]\s+/gm, '');
  // 7. Collapse excessive whitespace
  cleaned = cleaned.replace(/[ \t]+/g, ' ');

  return cleaned.trim();
};

export const parseMathSteps = (text) => {
  if (!text) return [];
  const sanitized = sanitizeMathText(text);
  const rawLines = sanitized.split('\n').map(l => l.trim()).filter(Boolean);

  const steps = [];
  let currentStep = { title: '', content: [] };

  rawLines.forEach((line) => {
    // Check if line looks like a step header (e.g. "Step 1: ...", "Case 1:", "First,", "Finally,")
    const stepMatch = line.match(/^(Step\s+\d+:?|Case\s+\d+:?|First,|Second,|Then,|Next,|Finally,|Conclusion:?|Lemma\s*\d*:?)/i);
    
    if (stepMatch) {
      if (currentStep.title || currentStep.content.length > 0) {
        steps.push(currentStep);
      }
      currentStep = {
        title: line,
        content: []
      };
    } else {
      if (!currentStep.title && steps.length === 0 && currentStep.content.length === 0) {
        currentStep.title = 'Mathematical Derivation';
      }
      currentStep.content.push(line);
    }
  });

  if (currentStep.title || currentStep.content.length > 0) {
    steps.push(currentStep);
  }

  // If no structured steps detected, return the whole text as lines
  if (steps.length === 0 && rawLines.length > 0) {
    return [{ title: 'Solution Steps', content: rawLines }];
  }

  return steps;
};
