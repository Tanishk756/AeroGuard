const navItems = [
  'Dashboard',
  'Users',
  'Roles',
  'Permissions',
  'Sessions',
  'Sensors',
  'Sensor Profiles',
  'Scenarios',
  'Threat Policies',
  'AI Models',
  'Datasets',
  'Feature Flags',
  'System Configuration',
  'Audit Logs',
  'System Health',
  'API Keys',
  'Data Management'
];

export default function App() {
  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <span className="brand-mark">A</span>
          <div>
            <strong>AeroGuard</strong>
            <small>Admin</small>
          </div>
        </div>

        <nav className="nav-list">
          {navItems.map((item) => (
            <button key={item} className="nav-item">
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <section className="admin-main">
        <header className="admin-header">
          <div>
            <p className="eyebrow">Administration</p>
            <h1>Platform Governance</h1>
          </div>
          <div className="status-pill success">Security Ready</div>
        </header>

        <section className="admin-grid">
          <div className="metric-panel">
            <span>Users</span>
            <strong>12</strong>
          </div>
          <div className="metric-panel">
            <span>Sessions</span>
            <strong>5</strong>
          </div>
          <div className="metric-panel">
            <span>System Health</span>
            <strong>Healthy</strong>
          </div>
          <div className="metric-panel">
            <span>Audit Events</span>
            <strong>2,451</strong>
          </div>
        </section>

        <section className="panel-list">
          <div className="panel">
            <div className="panel-header">
              <h2>Users</h2>
              <span className="status-pill info">CRUD</span>
            </div>
            <ul className="stack-list">
              <li>Create and manage users</li>
              <li>Role assignment</li>
              <li>Secure status controls</li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Roles & Permissions</h2>
              <span className="status-pill info">RBAC</span>
            </div>
            <ul className="stack-list">
              <li>Granular permission checks</li>
              <li>Server-side enforcement</li>
              <li>Role lifecycle</li>
            </ul>
          </div>

          <div className="panel">
            <div className="panel-header">
              <h2>Audit Logs</h2>
              <span className="status-pill warning">Trusted</span>
            </div>
            <ul className="stack-list">
              <li>Admin actions</li>
              <li>Authentication changes</li>
              <li>Security review</li>
            </ul>
          </div>
        </section>
      </section>
    </main>
  );
}
