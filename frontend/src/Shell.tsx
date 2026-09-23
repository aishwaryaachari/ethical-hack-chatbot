import { useEffect, useState } from 'react';
import { useAuth } from './auth';
import { getLlmStatus, listTopics, createTopic, deleteTopic } from './api';
import TopicDetail from './TopicDetail';

export interface Topic {
  topic_id: string; owner_id: string; tenant_id: string;
  title: string; created_at: string; doc_count: number;
}

export const MODELS = [
  { id: 'vulnerable', name: 'Qwen v1' },
  { id: 'protected', name: 'Qwen v2' },
];

export default function Shell({ mode, setMode }: { mode: string; setMode: (m: string) => void }) {
  const { user, logout } = useAuth();
  const [topics, setTopics] = useState<Topic[] | null>(null);
  const [openId, setOpenId] = useState<string | null>(() => {
    try { return localStorage.getItem('lab_open_topic'); } catch { return null; }
  });
  const [q, setQ] = useState('');
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState('');
  const [confirmDel, setConfirmDel] = useState<Topic | null>(null);
  const [llm, setLlm] = useState<any>({});
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  const load = async () => {
    if (!user) return;
    try {
      const list = (await listTopics(user.user_id)).topics || [];
      setTopics(list);
      // drop the restored topic if it was deleted elsewhere
      const saved = (() => { try { return localStorage.getItem('lab_open_topic'); } catch { return null; } })();
      if (saved && !list.some((t: Topic) => t.topic_id === saved)) {
        try { localStorage.removeItem('lab_open_topic'); } catch {}
        setOpenId(null);
      }
    } catch { setTopics([]); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    try {
      if (openId) localStorage.setItem('lab_open_topic', openId);
      else localStorage.removeItem('lab_open_topic');
    } catch {}
  }, [openId]);
  useEffect(() => { getLlmStatus().then(d => { setLlm(d); setBackendUp(true); }).catch(() => setBackendUp(false)); }, []);

  const open = (topics || []).find(t => t.topic_id === openId) ?? null;
  const modelName = MODELS.find(m => m.id === mode)?.name ?? MODELS[0].name;
  const displayName = (user?.email || '?').split('@')[0];
  const initial = (user?.email || '?').charAt(0).toUpperCase();
  const shown = (topics || []).filter(t => t.title.toLowerCase().includes(q.toLowerCase()));

  const doCreate = async () => {
    if (!user) return;
    const t = await createTopic(user.user_id, user.tenant_id, title || 'Untitled topic');
    setCreating(false); setTitle('');
    if (t.topic_id) { await load(); setOpenId(t.topic_id); }
  };

  return (
    <div className="app-top crt">
      {/* ---------- top horizontal navbar ---------- */}
      <header className="topnav2">
        {open ? (
          <>
            <button className="btn-tertiary" onClick={() => { setOpenId(null); load(); }}>←</button>
            <div className="wordmark" style={{ fontSize: 18 }}>{open.title}</div>
          </>
        ) : (
          <>
            <div className="wordmark">shieldlab<span className="dot">.</span></div>
            <input type="text" value={q} onChange={e => setQ(e.target.value)} placeholder="Search topics…"
              className="topsearch" />
            <button className="btn-primary" style={{ height: 38 }} onClick={() => { setTitle(''); setCreating(true); }}>
              + New topic
            </button>
          </>
        )}
        <div style={{ marginLeft: 'auto' }} />
        {!open && (
          <span className={`badge ${backendUp && llm.provider === 'groq' ? 'badge-live' : backendUp === false ? 'badge-err' : 'badge-sim'}`}>
            {backendUp === false ? 'backend down'
              : backendUp === null ? 'connecting…'
              : llm.provider === 'groq' ? `live · ${llm.model}` : 'local'}
          </span>
        )}
        <div className="profile-chip" title={user?.email}>
          <span className="avatar-circle">{initial}</span>
          <span className="company">{displayName}</span>
        </div>
        <button className="btn-tertiary" onClick={logout}>Sign out</button>
      </header>

      <main className="mainpane">
        {!open && (
          <div className="topics-wrap">
            <div className="topics-head">
              <h2>Topics</h2>
              <button className="btn-primary" onClick={() => { setTitle(''); setCreating(true); }}>+ New topic</button>
            </div>
            <p className="muted">One notebook per idea. Each topic keeps its own documents.</p>
            <div className="topic-grid">
              {shown.map(t => (
                <div key={t.topic_id} className="topic-card" onClick={() => setOpenId(t.topic_id)}>
                  <h3>{t.title}</h3>
                  <div className="meta">
                    <span className="badge">{t.doc_count} docs</span>
                    <span className="muted" style={{ fontSize: 16 }}>{(t.created_at || '').slice(0, 10)}</span>
                    <span className="del">
                      <button className="btn-tertiary" onClick={e => { e.stopPropagation(); setConfirmDel(t); }}>delete</button>
                    </span>
                  </div>
                </div>
              ))}
            </div>
            {topics !== null && !shown.length && (
              <div className="topic-card" style={{ cursor: 'default', textAlign: 'center', marginTop: 12 }}>
                <h3>No topics yet</h3>
                <p className="muted">Create your first topic, add PDFs to it, then chat with your documents.</p>
                <button className="btn-primary" onClick={() => setCreating(true)}>Create topic</button>
              </div>
            )}
          </div>
        )}
        {open && user && (
          <TopicDetail topic={open} user={user} mode={mode} setMode={setMode} modelName={modelName}
            onBack={() => { setOpenId(null); load(); }} onChanged={load} />
        )}
        {creating && (
          <div className="modal-veil" onClick={() => setCreating(false)}>
            <div className="modal" onClick={e => e.stopPropagation()}>
              <h3>New topic</h3>
              <p className="muted">Give your notebook a name. You'll add PDFs inside it next.</p>
              <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doCreate()} placeholder="e.g. Q3 invoices" />
              <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
                <button className="btn-secondary" onClick={() => setCreating(false)}>Cancel</button>
                <button className="btn-primary" onClick={doCreate}>Create</button>
              </div>
            </div>
          </div>
        )}
        {confirmDel && (
          <div className="modal-veil" onClick={() => setConfirmDel(null)}>
            <div className="modal" onClick={e => e.stopPropagation()}>
              <h3>Delete topic?</h3>
              <p className="muted">“{confirmDel.title}” and its {confirmDel.doc_count} document(s) will be removed.</p>
              <div style={{ display: 'flex', gap: 10, marginTop: 16, justifyContent: 'flex-end' }}>
                <button className="btn-secondary" onClick={() => setConfirmDel(null)}>Cancel</button>
                <button className="btn-primary" onClick={async () => {
                  if (user) await deleteTopic(confirmDel.topic_id, user.user_id);
                  setConfirmDel(null); load();
                }}>Delete</button>
              </div>
            </div>
          </div>
        )}
        <div className="statusbar">
          <span>shieldlabs-eval <span className="cu">{mode === 'vulnerable' ? 'qwen v1' : 'qwen v2'}</span></span>
          <span>sandbox <span className={backendUp && llm.provider === 'groq' ? 'ok' : ''}>
            {backendUp === false ? 'down' : backendUp === null ? '…' : llm.provider === 'groq' ? 'live' : 'local'}
          </span></span>
          <span>topics <span className="cu">{topics === null ? '…' : topics.length}</span></span>
          <span style={{ marginLeft: 'auto' }}>shieldlab_os <span className="cu">▮</span></span>
        </div>
      </main>
    </div>
  );
}
