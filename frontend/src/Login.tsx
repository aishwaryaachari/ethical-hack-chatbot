import { useState } from 'react';
import { useAuth } from './auth';

const TICKER = ['TOPICS', 'PDF SOURCES', 'NOTEBOOKS', 'GROUNDED CHAT', 'WORKSPACES'];

export default function Login() {
  const { users, usersFailed, login } = useAuth();
  const [email, setEmail] = useState('tanush@gmail.com');
  const [error, setError] = useState('');

  const visible = users;

  const submit = () => {
    const u = users.find(x => x.email.toLowerCase() === email.trim().toLowerCase());
    if (!u) { setError('Unknown account. Pick one from the workspace directory.'); return; }
    login(u.user_id);
  };

  const tickerRow = () => (
    <div className="marquee-track static">
      {TICKER.map((t, i) => (
        <span key={i}><b>▮</b> {t}</span>
      ))}
    </div>
  );

  return (
    <div className="login-wrap crt">
      <div className="login-brand">
        <div className="topbar">
          <span>shieldlab<span style={{ color: 'var(--copper)' }}>.</span> terminal</span>
          <span>sys.online <span className="blink">▮</span></span>
        </div>

        <div className="hero-full">
          <div className="hero-kicker">shieldlab_os // personal ai terminal</div>
          <h1>THINK.<br />ASK.<br /><span className="cu">BUILD.</span></h1>
          <p className="hero-sub">
            A personal AI notebook for your workspace. Create topics, attach PDFs
            to each one, and chat with answers grounded in your own documents.
          </p>
        </div>

        <div className="hero-stats">
          <div><div className="n">02</div><div className="l">models</div></div>
          <div><div className="n">03</div><div className="l">workspaces</div></div>
          <div><div className="n">24/7</div><div className="l">uptime</div></div>
        </div>

        <div className="marquee">{tickerRow()}</div>
      </div>

      <div className="login-pane">
        <div className="login-card">
          <div className="section-label">Sign in</div>
          <h2>Jack in</h2>
          <p className="muted">Use any workspace account below. Any password works here.</p>
          <label>Email</label>
          <input type="text" value={email} onChange={e => { setEmail(e.target.value); setError(''); }}
            onKeyDown={e => e.key === 'Enter' && submit()} placeholder="you@gmail.com" />
          <label>Password</label>
          <input type="text" placeholder="password (not checked)" onKeyDown={e => e.key === 'Enter' && submit()} />
          {error && <div className="verdict verdict-leak">{error}</div>}
          <button className="btn-primary" style={{ width: '100%', marginTop: 10 }} onClick={submit}>Sign in →</button>
          <div className="section-label" style={{ marginTop: 12 }}>Workspace directory</div>
          <div className="userdir">
            {usersFailed && (
              <div className="verdict verdict-leak">Backend unreachable — start it, then reload.</div>
            )}
            {!usersFailed && visible.length === 0 && (
              <div className="muted" style={{ padding: 10 }}>Loading accounts…</div>
            )}            {visible.map(u => (
              <button key={u.user_id} className="userdir-row" onClick={() => login(u.user_id)}>
                <span className="mono">{u.email.split('@')[0]}</span>
                <span className="muted" style={{ fontSize: 15 }}>{u.email}</span>
                <span className="badge">{u.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
