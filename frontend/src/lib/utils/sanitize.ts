const SAFE_SCHEMES = new Set(['http:', 'https:', 'mailto:', 'tel:']);

export function safeHref(raw: string | null | undefined): string {
  if (!raw) return '#';
  const trimmed = String(raw).trim();
  if (!trimmed) return '#';
  if (trimmed.startsWith('//')) {
    return `https:${trimmed}`;
  }
  if (trimmed.startsWith('/') || trimmed.startsWith('#') || trimmed.startsWith('?')) {
    return trimmed;
  }
  try {
    const u = new URL(trimmed);
    return SAFE_SCHEMES.has(u.protocol) ? trimmed : '#';
  } catch {
    return '#';
  }
}

const ALLOWED_TAGS = new Set([
  'b',
  'strong',
  'em',
  'i',
  'u',
  's',
  'span',
  'br',
  'p',
  'small',
  'code',
  'kbd',
  'sub',
  'sup'
]);

const ALLOWED_ATTRS = new Set(['class', 'title']);

export function sanitizeRichText(raw: string | null | undefined): string {
  if (!raw) return '';
  if (typeof DOMParser === 'undefined') return '';

  const doc = new DOMParser().parseFromString(`<div>${raw}</div>`, 'text/html');
  const root = doc.body.firstElementChild;
  if (!root) return '';

  const walk = (node: Element): void => {
    const children = Array.from(node.children);
    for (const child of children) {
      const tag = child.tagName.toLowerCase();
      if (!ALLOWED_TAGS.has(tag)) {
        const text = doc.createTextNode(child.textContent ?? '');
        child.replaceWith(text);
        continue;
      }
      for (const attr of Array.from(child.attributes)) {
        if (!ALLOWED_ATTRS.has(attr.name.toLowerCase())) {
          child.removeAttribute(attr.name);
        }
      }
      walk(child);
    }
  };

  walk(root);
  return root.innerHTML;
}
