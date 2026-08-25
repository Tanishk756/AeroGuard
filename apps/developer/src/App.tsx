const services = [
  { name: 'API Gateway', status: 'Healthy' },
  { name: 'Database', status: 'Ready' },
  { name: 'WebSocket', status: 'Connected' },
  { name: 'System Health', status: 'Nominal' }
];

export default function App() {
  return (
    <main className="developer-shell">
      <header className="developer-header">
        <div>
          <p className="eyebrow">Developer</p>
          <h1>API Console</h1>
        </div>
        <div className="status-pill success">OpenAPI Ready</div>
      </header>

      <section className="developer-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Services</h2>
          </div>
          <ul className="stack-list">
            {services.map((service) => (
              <li key={service.name} className="service-row">
                <span>{service.name}</span>
                <span className="status-dot success" />
                <strong>{service.status}</strong>
              </li>
            ))}
          </ul>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Environment</h2>
          </div>
          <ul className="stack-list">
            <li>App: AeroGuard</li>
            <li>Mode: Development</li>
            <li>Docs: OpenAPI</li>
            <li>Access: Protected</li>
          </ul>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Diagnostics</h2>
          </div>
          <ul className="stack-list">
            <li>Startup checks</li>
            <li>Schema validation</li>
            <li>API contract review</li>
            <li>Audit trace visibility</li>
          </ul>
        </div>
      </section>
    </main>
  );
}
