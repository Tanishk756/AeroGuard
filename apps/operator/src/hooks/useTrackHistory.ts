import { useEffect, useState } from 'react';
import { getTrackHistory } from '../api/tracks';
import { TrackHistoryPoint } from '../types';

export interface TrackHistoryHookReturn {
  historyPoints: TrackHistoryPoint[];
  isLoading: boolean;
  error: string | null;
  refreshHistory: () => Promise<void>;
}

export function useTrackHistory(trackId: string | null, limit = 50): TrackHistoryHookReturn {
  const [historyPoints, setHistoryPoints] = useState<TrackHistoryPoint[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    if (!trackId) {
      setHistoryPoints([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await getTrackHistory(trackId, limit);
      setHistoryPoints(response.items || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query trajectory history';
      setError(msg);
      setHistoryPoints([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isCancelled = false;

    if (!trackId) {
      setHistoryPoints([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    getTrackHistory(trackId, limit)
      .then((res) => {
        if (!isCancelled) {
          setHistoryPoints(res.items || []);
        }
      })
      .catch((err: unknown) => {
        if (!isCancelled) {
          const msg = err instanceof Error ? err.message : 'Failed to query trajectory history';
          setError(msg);
          setHistoryPoints([]);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [trackId, limit]);

  return {
    historyPoints,
    isLoading,
    error,
    refreshHistory: fetchHistory,
  };
}
