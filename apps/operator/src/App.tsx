export default function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">AeroGuard</p>
          <h1>Operator Console</h1>
        </div>
        <div className="status-pill success">System Online</div>
      </header>

      <nav className="sidebar">
        <div className="nav-section">
          <span className="nav-label">Workspace</span>
          <button>Overview</button>
          <button>Mission</button>
          <button>Threats</button>
        </div>
        <div className="nav-section">
          <span className="nav-label">Status</span>
          <button>System</button>
          <button>Alerts</button>
          <button>Audit</button>
        </div>
      </nav>

      <section className="workspace">
        <div className="panel map-panel">
          <div className="panel-header">
            <h2>Tactical Map</h2>
            <span className="status-pill info">Foundation</span>
          </div>
          <div className="map-surface">
            <div className="grid-overlay" />
          </div>
        </div>

        <div className="secondary-grid">
          <div className="panel">
            <div className="panel-header">
              <h2>Track Panel</h2>
            </div>
            <ul className="stack-list">
              <li>Track registry</li>
              <li>Sensor association</li>
              <li>Confidence metadata</li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Threat Panel</h2>
            </div>
            <ul className="stack-list">
              <li>Threat posture</li>
              <li>Assessment workflow</li>
              <li>Priority review</li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Alert Stream</h2>
            </div>
            <ul className="stack-list">
              <li>System status</li>
              <li>Audit events</li>
              <li>Operator notices</li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Mission Timeline</h2>
            </div>
            <ul className="stack-list">
              <li>Session timeline</li>
              <li>Review windows</li>
              <li>Replay-ready state</li>
            </ul>
          </div>
        </div>
      </section>
    </main>
  );
}
