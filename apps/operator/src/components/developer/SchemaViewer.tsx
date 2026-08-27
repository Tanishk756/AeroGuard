import React, { useState } from 'react';
import { SCHEMA_CATALOG } from '../../api/developer';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { SchemaDefinition } from '../../types/developer';

export const SchemaViewer: React.FC = () => {
  const [selectedSchemaName, setSelectedSchemaName] = useState<string>(SCHEMA_CATALOG[0].name);
  const [copiedSchema, setCopiedSchema] = useState<boolean>(false);

  const currentSchema: SchemaDefinition =
    SCHEMA_CATALOG.find((s) => s.name === selectedSchemaName) || SCHEMA_CATALOG[0];

  const handleCopySchemaJson = () => {
    const jsonExample: Record<string, unknown> = {};
    currentSchema.fields.forEach((f) => {
      jsonExample[f.name] = `<${f.type}> ${f.description}${f.constraints ? ` (${f.constraints})` : ''}`;
    });
    navigator.clipboard.writeText(JSON.stringify(jsonExample, null, 2));
    setCopiedSchema(true);
    setTimeout(() => setCopiedSchema(false), 2000);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 'var(--space-md)' }}>
      {/* Left Column: Schema List */}
      <Card title="Pydantic Data Models">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {SCHEMA_CATALOG.map((schema) => {
            const isSelected = selectedSchemaName === schema.name;
            return (
              <button
                key={schema.name}
                type="button"
                onClick={() => setSelectedSchemaName(schema.name)}
                className="tactical-btn"
                style={{
                  padding: '8px 10px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  backgroundColor: isSelected ? 'var(--bg-surface-active)' : 'transparent',
                  borderLeft: isSelected ? '3px solid var(--color-accent)' : '3px solid transparent',
                  textAlign: 'left',
                }}
              >
                <span className="font-mono text-sm" style={{ fontWeight: 600, color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)' }}>
                  {schema.name}
                </span>
                <span className="uppercase-tracking text-muted" style={{ fontSize: '9px' }}>
                  {schema.domain}
                </span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Right Column: Schema Fields & Specifications */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <Card
          title={`Schema Contract: ${currentSchema.name}`}
          actions={
            <Button variant="secondary" size="sm" onClick={handleCopySchemaJson}>
              {copiedSchema ? '✓ Copied' : 'Copy Sample Contract'}
            </Button>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
              {currentSchema.description}
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="tactical-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ width: '180px' }}>FIELD NAME</th>
                    <th style={{ width: '160px' }}>DATA TYPE</th>
                    <th style={{ width: '100px' }}>REQUIRED</th>
                    <th style={{ width: '180px' }}>CONSTRAINTS</th>
                    <th>FIELD DESCRIPTION</th>
                  </tr>
                </thead>
                <tbody>
                  {currentSchema.fields.map((field) => (
                    <tr key={field.name}>
                      <td>
                        <span className="font-mono text-xs" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {field.name}
                        </span>
                      </td>
                      <td>
                        <span className="font-mono text-xs text-muted">
                          {field.type}
                        </span>
                      </td>
                      <td>
                        <span
                          className="font-mono text-xs"
                          style={{
                            color: field.required ? 'var(--status-critical)' : 'var(--text-muted)',
                            fontWeight: field.required ? 600 : 400,
                          }}
                        >
                          {field.required ? 'REQUIRED' : 'OPTIONAL'}
                        </span>
                      </td>
                      <td>
                        {field.constraints ? (
                          <span
                            className="font-mono text-xs"
                            style={{
                              padding: '2px 6px',
                              backgroundColor: 'var(--bg-canvas)',
                              borderRadius: '3px',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--status-warning)',
                            }}
                          >
                            {field.constraints}
                          </span>
                        ) : (
                          <span className="text-muted text-xs">—</span>
                        )}
                      </td>
                      <td>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                          {field.description}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Static Contract Fallback Notice */}
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '11px',
                color: 'var(--text-muted)',
              }}
            >
              🔒 <strong>Schema Provenance</strong>: Model definitions reflect backend Pydantic contracts under <code className="font-mono">backend/app/schemas/</code>.
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
