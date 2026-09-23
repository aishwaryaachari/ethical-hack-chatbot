import { useEffect, useRef, useState } from 'react';
import { DemoUser } from './auth';
import { Topic } from './Shell';
import { queryDocs, uploadDoc, topicDocs, resetKb, deleteDoc } from './api';
import Markdown from './markdown';
import MatrixOrb, { MatrixOrbState } from './MatrixOrb';

interface Msg { id: string; role: 'user' | 'assistant'; text: string; sources?: string[] }

const storeKey = (tid: string) => `lab_topic_msgs_${tid}`;

const MODEL_OPTS = [
  { id: 'vulnerable', name: 'Qwen v1', desc: 'Standard · fast answers' },
  { id: 'protected', name: 'Qwen v2', desc: 'Enhanced · deeper reasoning' },
];

export default function TopicDetail({ topic, user, mode, setMode, modelName, onBack, onChanged }: {
  topic: Topic; user: DemoUser; mode: string; setMode: (m: string) => void; modelName: string;
  onBack: () => void; onChanged: () => void;
}) {
  const [msgs, setMsgs] = useState<Msg[]>(() => {
    try { return JSON.parse(localStorage.getItem(storeKey(topic.topic_id)) || '[]'); } catch { return []; }
  });
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [typing, setTyping] = useState(false);
  const [docs, setDocs] = useState<any[] | null>(null);
  const [srcQ, setSrcQ] = useState('');
  const [uploading, setUploading] = useState(false);
  const [upErr, setUpErr] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const modelRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) setModelOpen(false);
    };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setModelOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, []);

  useEffect(() => { localStorage.setItem(storeKey(topic.topic_id), JSON.stringify(msgs)); }, [msgs, topic.topic_id]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs, thinking]);

  const loadDocs = async () => {
    try {
      const d = (await topicDocs(topic.topic_id, user.user_id)).docs || [];
      setDocs(d); onChanged();
    } catch { setDocs([]); }
  };
  useEffect(() => { loadDocs(); }, []);

  const searchedRef = useRef(msgs.length > 0);
  const [busy, setBusy] = useState(false);

  // orb priority: thinking > listening (typing) > idle
  const orbState: MatrixOrbState = thinking ? 'thinking' : typing ? 'listening' : 'idle';

  const send = async (text?: string) => {
    const q = (text ?? input).trim();
    if (!q || thinking || busy) return;
    setInput(''); setTyping(false);
    const firstSearch = !searchedRef.current;
    searchedRef.current = true;
    setMsgs(m => [...m, { id: `m${Date.now()}`, role: 'user', text: q }]);
    // Thinking orb shows only on the first search, for at least 5 seconds.
    if (firstSearch) setThinking(true);
    else setBusy(true);
    try {
      const resP = queryDocs(q, user.user_id, user.tenant_id, mode, topic.topic_id);
      const waitP = firstSearch ? new Promise(r => setTimeout(r, 5000)) : Promise.resolve();
      const [res] = await Promise.all([resP, waitP]);
      const chunks = res.retrieved_chunks || res.blocked_chunks || [];
      setMsgs(m => [...m, {
        id: `m${Date.now()}a`, role: 'assistant',
        text: res.llm?.answer || '(no answer)',
        sources: chunks.slice(0, 3).map((c: any) => c.id || 'document'),
      }]);
    } catch (e: any) {
      setMsgs(m => [...m, { id: `m${Date.now()}e`, role: 'assistant',
        text: `Couldn't reach the server: ${e.message}. Is the backend running on :8000?` }]);
    } finally { setThinking(false); setBusy(false); }
  };

  const addFiles = async (files: FileList | undefined | null) => {
    const f = files?.[0];
    if (!f) return;
    setUploading(true); setUpErr('');
    try {
      const r = await uploadDoc(f, user.user_id, user.tenant_id, topic.topic_id);
      if (r.error) setUpErr(r.error);
      else loadDocs();
    } catch (e: any) { setUpErr(e.message); }
    finally { setUploading(false); }
  };

  const shownDocs = (docs || []).filter(d => (d.filename || '').toLowerCase().includes(srcQ.toLowerCase()));

  return (
    <div className="nb">
      {/* ---------- Sources rail ---------- */}
      <div className={`sources-rail${dragOver ? ' dragover' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3>Sources</h3>
          <span className="badge">{docs === null ? '…' : `${docs.length} saved`}</span>
        </div>
        <button className="btn-secondary" style={{ width: '100%' }} onClick={() => fileRef.current?.click()}>
          + Add sources
        </button>
        <input ref={fileRef} type="file" accept=".pdf" style={{ display: 'none' }}
          onChange={e => { addFiles(e.target.files); e.target.value = ''; }} />
        <input type="text" value={srcQ} onChange={e => setSrcQ(e.target.value)}
          placeholder="Search saved sources…" style={{ fontSize: 18, padding: '8px 10px' }} />
        {uploading && <div className="muted">Uploading… ▮</div>}
        {upErr && <div className="verdict verdict-leak">{upErr}</div>}
        <div className="source-list">
          {docs !== null && docs.length === 0 && !dragOver && (
            <div className="sources-empty">
              <div style={{ fontSize: 32 }}>▤</div>
              <div className="big">Saved sources will appear here</div>
              <div>Add PDFs, then ask questions grounded in these sources.</div>
              <div style={{ marginTop: 8 }}>Drop files here or <button className="btn-tertiary" onClick={() => fileRef.current?.click()}>add a source</button></div>
            </div>
          )}
          {dragOver && (
            <div className="sources-empty">
              <div className="big">Drop to add</div>
              <div>The PDF will be stored in this topic.</div>
            </div>
          )}
          {shownDocs.map((d: any) => (
            <div key={d.doc_id} className="source-row">
              <span className="dot">▮</span>
              <span className="fname">{d.filename}</span>
              <span className="badge" style={{ marginLeft: 'auto' }}>{d.chunks ?? '?'} ch</span>
              <button className="mini-del" title={`Delete ${d.filename}`}
                onClick={async () => {
                  if (!window.confirm(`Delete “${d.filename}” from this topic?`)) return;
                  await deleteDoc(d.doc_id, user.user_id);
                  loadDocs();
                }}>×</button>
            </div>
          ))}
        </div>
        <div className="muted" style={{ fontSize: 16 }}>{topic.title} · {modelName}</div>
        <button className="btn-tertiary" style={{ textAlign: 'left' }}
          title="Deletes EVERYTHING: all topics and all documents"
          onClick={async () => {
            if (!window.confirm('Reset EVERYTHING? All topics and all documents will be deleted.')) return;
            await resetKb();
            localStorage.removeItem(storeKey(topic.topic_id));
            onBack();
          }}>↺ Reset everything (all topics)</button>
      </div>

      {/* ---------- Chat canvas ---------- */}
      <div className="canvas">
        <div className="crumbs">
          <span>{topic.title}</span>
          <span style={{ marginLeft: 'auto' }} />
          <div className="modelpick" ref={modelRef}>
            <button className={`modelbtn${modelOpen ? ' open' : ''}`} onClick={() => setModelOpen(o => !o)}>
              <span className="mdot">◈</span> {modelName} <span className="chev">{modelOpen ? '▴' : '▾'}</span>
            </button>
            {modelOpen && (
              <div className="modelmenu">
                {MODEL_OPTS.map(o => (
                  <button key={o.id} className={`modelopt${o.id === mode ? ' sel' : ''}`}
                    onClick={() => { setMode(o.id); setModelOpen(false); }}>
                    <span className="mname">{o.id === mode ? '▮ ' : ''}{o.name}</span>
                    <span className="mdesc">{o.desc}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className="chat-scroll">
          {msgs.length === 0 && !thinking && (
            <div className="chat-welcome">
              <div className="orb-alive">
                <MatrixOrb state={orbState} size={200} color="#ed670f" forceMotion
                  labels={{ idle: 'Idle — ask about your documents' }} />
              </div>
              <p className="muted" style={{ maxWidth: 480, margin: '8px auto 0' }}>
                Try “summarize these documents”, “what are the key points?”,
                or “quote the relevant passage”.
              </p>
            </div>
          )}
          {msgs.map(m => (
            <div key={m.id} className={`msg ${m.role}`}>
              <div className="msg-head">
                <span className="badge">{m.role === 'user' ? user.email.split('@')[0] : modelName}</span>
              </div>
              <div className="msg-body">{m.role === 'assistant' ? <Markdown text={m.text} /> : m.text}</div>
              {m.sources && m.sources.length > 0 && (
                <div className="srcchips">
                  {m.sources.map((s, i) => <span key={i} className="badge">▮ {s}</span>)}
                </div>
              )}
            </div>
          ))}
          {thinking && (
            <div className="orb-alive" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '12px 0' }}>
              <MatrixOrb state="thinking" size={150} color="#ed670f" forceMotion />
            </div>
          )}
          <div ref={bottom} />
        </div>
        <div className="composer">
          <div className="composer-bar">
            <textarea value={input} onChange={e => { setInput(e.target.value); setTyping(e.target.value.length > 0); }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder="Ask a question or create something" rows={1} />
            <span className="count">{docs === null ? '…' : `${docs.length} sources`}</span>
            <button className="sendbtn" disabled={thinking || busy || !input.trim()} onClick={() => send()}>↑</button>
          </div>
          <div className="disclaimer">
            <span className="muted" style={{ fontSize: 16 }}>Answers use only this topic's sources. Double-check important claims.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
