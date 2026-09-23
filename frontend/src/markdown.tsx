// Tiny safe markdown renderer (no dangerouslySetInnerHTML).
// Supports: ###/##/# headings, - and 1. lists, **bold**, *italic*, `code`.
import React from 'react';

function inline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)/g;
  let last = 0, m: RegExpExecArray | null, i = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) parts.push(<strong key={`${keyPrefix}-${i++}`}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith('`')) parts.push(<code key={`${keyPrefix}-${i++}`}>{tok.slice(1, -1)}</code>);
    else parts.push(<em key={`${keyPrefix}-${i++}`}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

export default function Markdown({ text }: { text: string }) {
  const lines = (text || '').split('\n');
  const out: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let k = 0;

  const flushList = () => {
    if (!list) return;
    const items = list.items.map((it, i) => <li key={i}>{inline(it, `li${k}-${i}`)}</li>);
    out.push(list.ordered
      ? <ol key={`l${k++}`}>{items}</ol>
      : <ul key={`l${k++}`}>{items}</ul>);
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trim();
    const h = line.match(/^(#{1,3})\s+(.*)/);
    const ul = line.match(/^[-*]\s+(.*)/);
    const ol = line.match(/^\d+[.)]\s+(.*)/);
    if (h) {
      flushList();
      const lvl = h[1].length;
      out.push(lvl === 1
        ? <h4 key={`h${k++}`}>{inline(h[2], `h${k}`)}</h4>
        : lvl === 2
          ? <h5 key={`h${k++}`}>{inline(h[2], `h${k}`)}</h5>
          : <h6 key={`h${k++}`}>{inline(h[2], `h${k}`)}</h6>);
    } else if (ul || ol) {
      const ordered = !!ol;
      const item = (ul ? ul[1] : ol![1]);
      if (!list || list.ordered !== ordered) { flushList(); list = { ordered, items: [] }; }
      list.items.push(item);
    } else if (!line) {
      flushList();
    } else {
      flushList();
      out.push(<p key={`p${k++}`}>{inline(line, `p${k}`)}</p>);
    }
  }
  flushList();
  return <div className="md">{out}</div>;
}
