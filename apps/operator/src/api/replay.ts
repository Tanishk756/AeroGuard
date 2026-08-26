import {
  ReplayComparisonReport,
  ReplayComparisonRequest,
  ReplayRequest,
  ReplaySnapshot,
  ReplayStepRequest,
} from '../types';
import { request } from './client';

export async function queryReplaySnapshot(req: ReplayRequest): Promise<ReplaySnapshot> {
  return request<ReplaySnapshot>('/replay/query', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function stepReplay(req: ReplayStepRequest): Promise<ReplaySnapshot> {
  return request<ReplaySnapshot>('/replay/step', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function compareReplay(req: ReplayComparisonRequest): Promise<ReplayComparisonReport> {
  return request<ReplayComparisonReport>('/replay/compare', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
