import { useCallback, useRef, useState } from 'react';
import {
  getAnalyticsSummary,
  getDetectionMetrics,
  getTrackMetrics,
  getAlertMetrics,
  getThreatMetrics,
} from '../api/analytics';
import {
  AnalyticsSummaryResponse,
} from '../types';

export interface AnalyticsQueryParams {
  windowStart?: string;
  windowEnd?: string;
}

/**
 * Hook that orchestrates fetching of all analytics endpoints.
 *
 * Stale-request protection: an AbortController ref is maintained; when a new
 * fetch is triggered, the previous request is aborted before starting.
 *
 * CSV helper: generateCsv() escapes per RFC 4180 and enforces a configurable
 * row limit.
 */
export const useAnalytics = () => {
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useState<AnalyticsQueryParams>({});

  // Abort controller ref for stale-request protection.
  const controllerRef = useRef<AbortController | null>(null);

  const fetchAll = useCallback(async (overrideParams?: AnalyticsQueryParams) => {
    // Abort any in-flight request before starting a new one.
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    const p = overrideParams ?? params;
    const apiParams = {
      window_start: p.windowStart,
      window_end: p.windowEnd,
    };

    setLoading(true);
    setError(null);

    try {
      const summaryData = await getAnalyticsSummary(apiParams);

      // Ignore results if this request was superseded.
      if (controller.signal.aborted) return;

      setSummary(summaryData);
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof Error ? e.message : 'Failed to load analytics');
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [params]);

  const setWindow = (start?: string, end?: string) => {
    setParams({ windowStart: start, windowEnd: end });
  };

  /**
   * Generate a CSV string from a list of records.
   * Escapes per RFC 4180:
   *   - Quotes doubled inside quoted fields.
   *   - Fields containing commas, quotes, or newlines are surrounded by double quotes.
   *   - Empty values produce empty fields.
   * Row limit: rows beyond maxRows are silently dropped (caller should warn the user).
   */
  const generateCsv = (
    data: Record<string, unknown>[],
    headers: string[],
    maxRows = 10_000,
  ): string => {
    const escapeField = (value: unknown): string => {
      if (value === null || value === undefined) return '';
      const str = String(value);
      if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const limitedData = data.slice(0, maxRows);
    const rows: string[] = [headers.map(escapeField).join(',')];
    for (const row of limitedData) {
      rows.push(headers.map((h) => escapeField(row[h])).join(','));
    }
    return rows.join('\n');
  };

  return {
    summary,
    loading,
    error,
    fetchAll,
    setWindow,
    generateCsv,
  };
};
