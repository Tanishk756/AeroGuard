import React, { useEffect, useState } from 'react';
import {
  API_CATALOG,
  buildQueryString,
  dispatchApiRequest,
  generateCurlCommand,
  generateFetchSnippet,
  interpolatePath,
} from '../../api/developer';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { ApiEndpoint, DispatchedResponse } from '../../types/developer';

interface RequestDispatcherProps {
  initialEndpoint?: ApiEndpoint;
  onEndpointChanged?: (endpoint: ApiEndpoint) => void;
}

export const RequestDispatcher: React.FC<RequestDispatcherProps> = ({
  initialEndpoint,
  onEndpointChanged,
}) => {
  const { hasPermission, hasAnyPermission, user } = useAuth();
  const [selectedEndpointId, setSelectedEndpointId] = useState<string>(
    initialEndpoint?.id || API_CATALOG[0].id
  );
  const [pathParams, setPathParams] = useState<Record<string, string>>({});
  const [queryParams, setQueryParams] = useState<Record<string, string>>({});
  const [requestBody, setRequestBody] = useState<string>('');
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [response, setResponse] = useState<DispatchedResponse | null>(null);
  const [showHeaders, setShowHeaders] = useState<boolean>(false);
  const [activeSnippetTab, setActiveSnippetTab] = useState<'powershell' | 'posix' | 'fetch'>('powershell');
  const [copiedSnippet, setCopiedSnippet] = useState<boolean>(false);
  const [copiedResponse, setCopiedResponse] = useState<boolean>(false);

  const currentEndpoint = API_CATALOG.find((e) => e.id === selectedEndpointId) || API_CATALOG[0];

  // Synchronize when initialEndpoint prop changes
  useEffect(() => {
    if (initialEndpoint && initialEndpoint.id !== selectedEndpointId) {
      setSelectedEndpointId(initialEndpoint.id);
    }
  }, [initialEndpoint, selectedEndpointId]);

  // Reset parameters and body template on endpoint change
  useEffect(() => {
    const initialPathParams: Record<string, string> = {};
    if (currentEndpoint.pathParams) {
      currentEndpoint.pathParams.forEach((p) => {
        initialPathParams[p.name] = (p.defaultValue as string) || '';
      });
    }
    setPathParams(initialPathParams);

    const initialQueryParams: Record<string, string> = {};
    if (currentEndpoint.queryParams) {
      currentEndpoint.queryParams.forEach((q) => {
        if (q.defaultValue !== undefined) {
          initialQueryParams[q.name] = String(q.defaultValue);
        }
      });
    }
    setQueryParams(initialQueryParams);

    setRequestBody(currentEndpoint.requestBodyTemplate || '');
    setJsonError(null);
    setResponse(null);
  }, [currentEndpoint]);

  const handleSelectEndpoint = (id: string) => {
    setSelectedEndpointId(id);
    const ep = API_CATALOG.find((e) => e.id === id);
    if (ep && onEndpointChanged) {
      onEndpointChanged(ep);
    }
  };

  const handlePathParamChange = (name: string, value: string) => {
    setPathParams((prev) => ({ ...prev, [name]: value }));
  };

  const handleQueryParamChange = (name: string, value: string) => {
    setQueryParams((prev) => ({ ...prev, [name]: value }));
  };

  const handleBodyChange = (value: string) => {
    setRequestBody(value);
    if (!value.trim()) {
      setJsonError(null);
      return;
    }
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch (err) {
      setJsonError(err instanceof Error ? err.message : 'Invalid JSON format');
    }
  };

  const handleFormatJson = () => {
    if (!requestBody.trim()) return;
    try {
      const parsed = JSON.parse(requestBody);
      setRequestBody(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch {
      // Keep existing
    }
  };

  const hasAccess = () => {
    if (currentEndpoint.requiredPermission) {
      return hasPermission(currentEndpoint.requiredPermission);
    }
    if (currentEndpoint.requiredAnyPermissions) {
      return hasAnyPermission(currentEndpoint.requiredAnyPermissions);
    }
    return true;
  };

  const resolvedUrl = `/api/v1${interpolatePath(currentEndpoint.path, pathParams)}${buildQueryString(queryParams)}`;
  const fullAbsoluteUrl = `http://localhost:8000${resolvedUrl}`;

  const handleExecute = async () => {
    if (jsonError && ['POST', 'PUT', 'PATCH'].includes(currentEndpoint.method)) {
      return;
    }

    setIsExecuting(true);
    try {
      const res = await dispatchApiRequest(currentEndpoint, pathParams, queryParams, requestBody);
      setResponse(res);
    } finally {
      setIsExecuting(false);
    }
  };

  const generatedSnippet = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (activeSnippetTab === 'powershell') {
      return generateCurlCommand(currentEndpoint.method, fullAbsoluteUrl, headers, requestBody, 'powershell');
    }
    if (activeSnippetTab === 'posix') {
      return generateCurlCommand(currentEndpoint.method, fullAbsoluteUrl, headers, requestBody, 'posix');
    }
    return generateFetchSnippet(currentEndpoint.method, resolvedUrl, headers, requestBody);
  };

  const handleCopySnippet = () => {
    navigator.clipboard.writeText(generatedSnippet());
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const handleCopyResponse = () => {
    if (!response) return;
    navigator.clipboard.writeText(JSON.stringify(response.data, null, 2));
    setCopiedResponse(true);
    setTimeout(() => setCopiedResponse(false), 2000);
  };

  const isPostOrPut = ['POST', 'PUT', 'PATCH'].includes(currentEndpoint.method);
  const authorized = hasAccess();

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1fr) minmax(340px, 1fr)', gap: 'var(--space-md)' }}>
      {/* Left Column: Request Configuration */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <Card title="API Request Builder">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {/* Endpoint Selector */}
            <div>
              <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '4px' }}>
                Select API Endpoint
              </label>
              <select
                className="tactical-input"
                value={selectedEndpointId}
                onChange={(e) => handleSelectEndpoint(e.target.value)}
                style={{ width: '100%' }}
              >
                {API_CATALOG.map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    [{ep.method}] {ep.path} — {ep.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Endpoint Meta Bar */}
            <div
              style={{
                padding: '10px 12px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    className="font-mono text-xs"
                    style={{
                      padding: '2px 6px',
                      borderRadius: '3px',
                      fontWeight: 700,
                      backgroundColor: 'var(--bg-surface-elevated)',
                      color: 'var(--color-accent)',
                      border: '1px solid var(--border-medium)',
                    }}
                  >
                    {currentEndpoint.method}
                  </span>
                  <span className="font-mono text-xs" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {resolvedUrl}
                  </span>
                </div>
                <StatusBadge
                  status={authorized ? 'ACTIVE' : 'CRITICAL'}
                  label={authorized ? 'AUTHORIZED' : 'PERMISSION REQUIRED'}
                />
              </div>

              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                {currentEndpoint.description}
              </div>

              {currentEndpoint.requiredPermission && (
                <div style={{ fontSize: '11px', color: authorized ? 'var(--status-active)' : 'var(--status-critical)' }}>
                  Requires permission: <code className="font-mono">{currentEndpoint.requiredPermission}</code>
                </div>
              )}
            </div>

            {/* Path Parameters Section */}
            {currentEndpoint.pathParams && currentEndpoint.pathParams.length > 0 && (
              <div>
                <span className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '6px' }}>
                  Path Parameters
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {currentEndpoint.pathParams.map((param) => (
                    <div key={param.name} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                        <span className="font-mono" style={{ color: 'var(--color-accent)' }}>
                          {'{' + param.name + '}'} {param.required && <span style={{ color: 'var(--status-critical)' }}>*</span>}
                        </span>
                        <span className="text-muted">{param.description}</span>
                      </div>
                      <input
                        type="text"
                        className="tactical-input"
                        value={pathParams[param.name] || ''}
                        onChange={(e) => handlePathParamChange(param.name, e.target.value)}
                        placeholder={`Enter ${param.name}...`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Query Parameters Section */}
            {currentEndpoint.queryParams && currentEndpoint.queryParams.length > 0 && (
              <div>
                <span className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '6px' }}>
                  Query Parameters
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {currentEndpoint.queryParams.map((param) => (
                    <div key={param.name} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                        <span className="font-mono text-muted">{param.name}</span>
                      </div>
                      <input
                        type="text"
                        className="tactical-input"
                        value={queryParams[param.name] !== undefined ? queryParams[param.name] : ''}
                        onChange={(e) => handleQueryParamChange(param.name, e.target.value)}
                        placeholder={param.description}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Request Body Editor */}
            {isPostOrPut && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                    JSON Request Body {currentEndpoint.requestBodySchema && `(${currentEndpoint.requestBodySchema})`}
                  </span>
                  <button
                    type="button"
                    onClick={handleFormatJson}
                    className="tactical-btn"
                    style={{ padding: '2px 6px', fontSize: '10px' }}
                  >
                    Format JSON
                  </button>
                </div>
                <textarea
                  className="tactical-input font-mono"
                  value={requestBody}
                  onChange={(e) => handleBodyChange(e.target.value)}
                  rows={8}
                  style={{
                    width: '100%',
                    fontSize: '11px',
                    lineHeight: '1.4',
                    fontFamily: 'monospace',
                    borderColor: jsonError ? 'var(--status-critical)' : undefined,
                  }}
                  placeholder="Enter JSON payload..."
                />
                {jsonError && (
                  <span style={{ fontSize: '11px', color: 'var(--status-critical)', marginTop: '2px', display: 'block' }}>
                    Syntax Error: {jsonError}
                  </span>
                )}
              </div>
            )}

            {/* Action Bar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 'var(--space-xs)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="font-mono text-xs text-muted">
                  ACTOR: {user?.username || 'ANONYMOUS'}
                </span>
              </div>
              <Button
                variant="primary"
                onClick={handleExecute}
                isLoading={isExecuting}
                disabled={Boolean(jsonError && isPostOrPut)}
              >
                Execute Request ⚡
              </Button>
            </div>
          </div>
        </Card>

        {/* Code Generation Snippet Box */}
        <Card title="Integration Code Generator">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  type="button"
                  onClick={() => setActiveSnippetTab('powershell')}
                  className="tactical-btn"
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    backgroundColor: activeSnippetTab === 'powershell' ? 'var(--color-accent)' : 'var(--bg-canvas)',
                    color: activeSnippetTab === 'powershell' ? '#000' : 'var(--text-secondary)',
                    fontWeight: activeSnippetTab === 'powershell' ? 700 : 400,
                  }}
                >
                  PowerShell cURL
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSnippetTab('posix')}
                  className="tactical-btn"
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    backgroundColor: activeSnippetTab === 'posix' ? 'var(--color-accent)' : 'var(--bg-canvas)',
                    color: activeSnippetTab === 'posix' ? '#000' : 'var(--text-secondary)',
                    fontWeight: activeSnippetTab === 'posix' ? 700 : 400,
                  }}
                >
                  POSIX cURL
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSnippetTab('fetch')}
                  className="tactical-btn"
                  style={{
                    padding: '3px 8px',
                    fontSize: '11px',
                    backgroundColor: activeSnippetTab === 'fetch' ? 'var(--color-accent)' : 'var(--bg-canvas)',
                    color: activeSnippetTab === 'fetch' ? '#000' : 'var(--text-secondary)',
                    fontWeight: activeSnippetTab === 'fetch' ? 700 : 400,
                  }}
                >
                  fetch() Snippet
                </button>
              </div>

              <Button variant="secondary" size="sm" onClick={handleCopySnippet}>
                {copiedSnippet ? '✓ Copied' : 'Copy Code'}
              </Button>
            </div>

            <pre
              className="font-mono"
              style={{
                margin: 0,
                padding: '10px',
                backgroundColor: 'var(--bg-canvas)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                overflowX: 'auto',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {generatedSnippet()}
            </pre>
          </div>
        </Card>
      </div>

      {/* Right Column: Response Telemetry & Payload */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <Card title="Live Response & Telemetry Inspector">
          {response ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              {/* Telemetry Metrics Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 'var(--space-xs)' }}>
                <div
                  style={{
                    padding: '8px',
                    backgroundColor: 'var(--bg-canvas)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div className="uppercase-tracking text-muted" style={{ fontSize: '9px' }}>HTTP Status</div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '2px' }}>
                    <span
                      className="font-mono"
                      style={{
                        fontSize: 'var(--text-md)',
                        fontWeight: 700,
                        color: response.ok ? 'var(--status-active)' : 'var(--status-critical)',
                      }}
                    >
                      {response.status || 'ERR'}
                    </span>
                    <span className="text-muted text-xs">{response.statusText}</span>
                  </div>
                </div>

                <div
                  style={{
                    padding: '8px',
                    backgroundColor: 'var(--bg-canvas)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div className="uppercase-tracking text-muted" style={{ fontSize: '9px' }}>Execution Latency</div>
                  <div className="font-mono" style={{ fontSize: 'var(--text-md)', fontWeight: 700, marginTop: '2px', color: 'var(--color-accent)' }}>
                    {response.durationMs} ms
                  </div>
                </div>

                <div
                  style={{
                    padding: '8px',
                    backgroundColor: 'var(--bg-canvas)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    gridColumn: 'span 2',
                  }}
                >
                  <div className="uppercase-tracking text-muted" style={{ fontSize: '9px' }}>Correlation ID</div>
                  <div className="font-mono text-xs" style={{ marginTop: '2px', color: 'var(--text-primary)', wordBreak: 'break-all' }}>
                    {response.correlationId || 'N/A'}
                  </div>
                </div>
              </div>

              {/* Response Headers Toggle */}
              <div>
                <button
                  type="button"
                  onClick={() => setShowHeaders(!showHeaders)}
                  className="tactical-btn"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                >
                  {showHeaders ? '▾ Hide Response Headers' : '▸ Show Response Headers'}
                </button>
                {showHeaders && (
                  <pre
                    className="font-mono"
                    style={{
                      marginTop: '6px',
                      padding: '8px',
                      backgroundColor: 'var(--bg-canvas)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '11px',
                      border: '1px solid var(--border-subtle)',
                      maxHeight: '160px',
                      overflowY: 'auto',
                    }}
                  >
                    {Object.entries(response.headers)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join('\n')}
                  </pre>
                )}
              </div>

              {/* Response Body Payload */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                    Response Body (JSON)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyResponse}
                    className="tactical-btn"
                    style={{ padding: '2px 6px', fontSize: '10px' }}
                  >
                    {copiedResponse ? '✓ Copied' : 'Copy Response'}
                  </button>
                </div>
                <pre
                  className="font-mono"
                  style={{
                    margin: 0,
                    padding: '12px',
                    backgroundColor: 'var(--bg-canvas)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '11px',
                    lineHeight: '1.4',
                    maxHeight: '440px',
                    overflowY: 'auto',
                    border: '1px solid var(--border-subtle)',
                    color: response.ok ? '#a7f3d0' : '#fca5a5',
                  }}
                >
                  {response.data !== null ? JSON.stringify(response.data, null, 2) : response.error || 'Empty body (204)'}
                </pre>
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: 'var(--space-xl)',
                textAlign: 'center',
                color: 'var(--text-muted)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <span style={{ fontSize: '24px' }}>⚡</span>
              <span>Execute an API request to view live server telemetry, status code, and JSON payload.</span>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
