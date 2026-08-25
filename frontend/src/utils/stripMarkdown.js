// Strips markdown syntax so TTS reads natural words instead of literal
// asterisks/hashes/pipes. Order matters: block-level constructs (tables,
// code fences) are unwrapped before inline emphasis markers are stripped.
export function stripMarkdownForSpeech(text) {
  if (!text) return '';

  let out = text;

  // Fenced code blocks -> just their content, on one line.
  out = out.replace(/```[\w-]*\n?([\s\S]*?)```/g, (_, code) => code.replace(/\n+/g, '. '));
  // Inline code
  out = out.replace(/`([^`]+)`/g, '$1');

  // Images: drop entirely (alt text rarely reads well aloud)
  out = out.replace(/!\[([^\]]*)\]\([^)]*\)/g, '');
  // Links: keep the label, drop the URL
  out = out.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1');

  // Headings
  out = out.replace(/^#{1,6}\s+/gm, '');
  // Blockquotes
  out = out.replace(/^>\s?/gm, '');
  // Horizontal rules
  out = out.replace(/^(-{3,}|\*{3,}|_{3,})$/gm, '');

  // Table pipes -> commas, drop separator rows entirely
  out = out.replace(/^\|?[\s:|-]+\|?$/gm, '');
  out = out.replace(/\|/g, ', ');

  // Bold / italic / strikethrough markers (any order, any nesting depth)
  out = out.replace(/(\*\*\*|___)(.*?)\1/g, '$2');
  out = out.replace(/(\*\*|__)(.*?)\1/g, '$2');
  out = out.replace(/(\*|_)(.*?)\1/g, '$2');
  out = out.replace(/~~(.*?)~~/g, '$1');

  // List markers
  out = out.replace(/^\s*[-*+]\s+/gm, '');
  out = out.replace(/^\s*\d+\.\s+/gm, '');
  // Task list checkboxes
  out = out.replace(/^\s*\[[ xX]\]\s*/gm, '');

  // Collapse whitespace left behind by the removals above.
  out = out.replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '. ').replace(/\n/g, ' ').trim();

  return out;
}
