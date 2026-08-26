import React from 'react';
import { Card } from '../../components/common/Card';
import { LoadingState } from '../../components/common/LoadingState';
import { ErrorState } from '../../components/common/ErrorState';
import { EmptyState } from '../../components/common/EmptyState';

interface AnalyticsTableProps<T> {
  title: string;
  data: T[] | null;
  columns: { key: keyof T; label: string }[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  onExportCsv: (headers: string[]) => void;
}

export function AnalyticsTable<T extends Record<string, any>>({
  title,
  data,
  columns,
  loading,
  error,
  onRefresh,
  onExportCsv,
}: AnalyticsTableProps<T>) {
  const headers = columns.map((c) => c.label);

  const handleExport = () => {
    onExportCsv(headers);
  };

  return (
    <Card title={title} actions={<>
      <button onClick={onRefresh} className="btn btn-sm">Refresh</button>
      <button onClick={handleExport} className="btn btn-sm ml-2">Export CSV</button>
    </>}>
      {error && <ErrorState message={error} onRetry={onRefresh} />}
      {loading && <LoadingState message="Loading..." />}
      {!loading && !error && (!data || data.length === 0) && (
        <EmptyState title="No Data" description="No records returned for the selected period." />
      )}
      {!loading && !error && data && data.length > 0 && (
        <table className="w-full text-sm" role="grid">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={String(col.key)} className="text-left px-2 py-1 border-b">{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-gray-800' : ''}>
                {columns.map((col) => (
                  <td key={String(col.key)} className="px-2 py-1 border-b">
                    {row[col.key] as unknown as React.ReactNode}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
