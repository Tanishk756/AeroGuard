/**
 * AeroGuard Incident Management API Client
 * Stage IM1-E: Operator Incident Workspace
 */

import {
  AcknowledgeIncidentRequest,
  AddIncidentNoteRequest,
  AssignIncidentRequest,
  CloseIncidentRequest,
  CreateIncidentExportRequest,
  CreateIncidentRequest,
  DeEscalateIncidentRequest,
  EscalateIncidentRequest,
  Incident,
  IncidentAnalyticsFilterParams,
  IncidentAnalyticsResponse,
  IncidentEvent,
  IncidentExportFilterParams,
  IncidentExportMetadata,
  IncidentExportResponse,
  IncidentFilterParams,
  IncidentListResponse,
  IntegrityCheckResponse,
  IntegritySummaryResponse,
  IntegrityVerificationBatchResponse,
  LogDefensiveActionRequest,
  PresignedArchiveDownloadResponse,
  ResolveIncidentRequest,
  StorageHealthResponse,
  TriageIncidentRequest,
} from '../types';
import { request } from './client';

export async function getIncidents(params?: IncidentFilterParams): Promise<IncidentListResponse> {
  return request<IncidentListResponse>('incidents', {
    method: 'GET',
    params: params as Record<string, string | number | boolean | undefined | null>,
  });
}

export async function getIncidentAnalytics(
  params?: IncidentAnalyticsFilterParams
): Promise<IncidentAnalyticsResponse> {
  return request<IncidentAnalyticsResponse>('incidents/analytics', {
    method: 'GET',
    params: params as Record<string, string | number | boolean | undefined | null>,
  });
}

export async function getIncident(id: string): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}`, {
    method: 'GET',
  });
}

export async function getIncidentTimeline(id: string): Promise<IncidentEvent[]> {
  return request<IncidentEvent[]>(`incidents/${encodeURIComponent(id)}/timeline`, {
    method: 'GET',
  });
}

export async function createIncident(data: CreateIncidentRequest): Promise<Incident> {
  return request<Incident>('incidents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function acknowledgeIncident(
  id: string,
  data?: AcknowledgeIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  });
}

export async function assignIncident(
  id: string,
  data: AssignIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/assign`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function triageIncident(
  id: string,
  data: TriageIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/triage`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function escalateIncident(
  id: string,
  data: EscalateIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/escalate`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deEscalateIncident(
  id: string,
  data: DeEscalateIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/de-escalate`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function resolveIncident(
  id: string,
  data: ResolveIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/resolve`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function closeIncident(
  id: string,
  data?: CloseIncidentRequest
): Promise<Incident> {
  return request<Incident>(`incidents/${encodeURIComponent(id)}/close`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  });
}

export async function addIncidentNote(
  id: string,
  data: AddIncidentNoteRequest
): Promise<IncidentEvent> {
  return request<IncidentEvent>(`incidents/${encodeURIComponent(id)}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function logDefensiveAction(
  id: string,
  data: LogDefensiveActionRequest
): Promise<IncidentEvent> {
  return request<IncidentEvent>(`incidents/${encodeURIComponent(id)}/actions`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function createIncidentExport(
  data: CreateIncidentExportRequest
): Promise<IncidentExportResponse> {
  return request<IncidentExportResponse>('incidents/export', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getIncidentExport(idOrNumber: string): Promise<IncidentExportResponse> {
  return request<IncidentExportResponse>(`incidents/export/${encodeURIComponent(idOrNumber)}`, {
    method: 'GET',
  });
}

export async function getIncidentExportHistory(
  params?: IncidentExportFilterParams
): Promise<IncidentExportMetadata[]> {
  return request<IncidentExportMetadata[]>('incidents/export', {
    method: 'GET',
    params: params as Record<string, string | number | boolean | undefined | null>,
  });
}

export async function getIncidentArchiveDownloadUrl(
  archiveId: string,
  expiresInSeconds: number = 300
): Promise<PresignedArchiveDownloadResponse> {
  return request<PresignedArchiveDownloadResponse>(`incidents/retention/archives/${archiveId}/download-url`, {
    method: 'GET',
    params: { expires_in_seconds: expiresInSeconds },
  });
}

export async function getIncidentStorageHealth(): Promise<StorageHealthResponse> {
  return request<StorageHealthResponse>('incidents/retention/storage/health', {
    method: 'GET',
  });
}

export async function getIntegritySummary(): Promise<IntegritySummaryResponse> {
  return request<IntegritySummaryResponse>('incidents/retention/integrity/summary', {
    method: 'GET',
  });
}

export async function getIntegrityChecks(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<IntegrityCheckResponse[]> {
  return request<IntegrityCheckResponse[]>('incidents/retention/integrity', {
    method: 'GET',
    params: params as Record<string, string | number | boolean | undefined | null>,
  });
}

export async function triggerBatchIntegrityCheck(
  limit: number = 100
): Promise<IntegrityVerificationBatchResponse> {
  return request<IntegrityVerificationBatchResponse>('incidents/retention/integrity/check', {
    method: 'POST',
    params: { limit },
  });
}

export async function verifySingleArchiveIntegrity(
  archiveId: string
): Promise<IntegrityCheckResponse> {
  return request<IntegrityCheckResponse>(`incidents/retention/archives/${archiveId}/verify`, {
    method: 'POST',
  });
}
