import { Component, ReactNode } from 'react';

interface State { error: Error | null; info: string }

export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null, info: '' };

  static getDerivedStateFromError(error: Error): State {
    return { error, info: '' };
  }

  componentDidCatch(error: Error, info: any) {
    this.setState({ info: info?.componentStack || '' });
    console.error('[shieldlab] render crash:', error);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ background: '#16120f', color: '#cecdc9', minHeight: '100vh', padding: 32, fontFamily: 'monospace' }}>
        <h2 style={{ color: '#ed670f' }}>shieldlab failed to render</h2>
        <p>Copy this error back to the chat so it can be fixed:</p>
        <pre style={{ background: '#201c19', border: '1px solid #ed670f', padding: 16, whiteSpace: 'pre-wrap' }}>
          {String(this.state.error?.message || this.state.error)}
          {this.state.info}
        </pre>
        <button onClick={() => { localStorage.clear(); location.reload(); }}>
          Clear saved data + reload
        </button>
      </div>
    );
  }
}

export function installGlobalProbe() {
  window.addEventListener('error', (e) => {
    console.error('[shieldlab] window.onerror:', e.message, e.filename, e.lineno);
  });
  // Boot probe: if React never mounts, replace the white screen with a diagnosis.
  setTimeout(() => {
    const root = document.getElementById('root');
    if (root && root.children.length === 0) {
      root.innerHTML =
        '<div style="background:#16120f;color:#cecdc9;min-height:100vh;padding:48px;font-family:monospace">' +
        '<h2 style="color:#ed670f">shieldlab did not boot</h2>' +
        '<p>JS bundle failed to load or crashed before first render. Open DevTools console (F12) and copy the red error.</p>' +
        '<p>Common fixes: hard-refresh (Ctrl+Shift+R), restart `npm run dev`, delete <code>node_modules/.vite</code>.</p></div>';
    }
  }, 6000);
}
