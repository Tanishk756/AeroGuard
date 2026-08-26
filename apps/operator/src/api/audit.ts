import { AuditEvent, AuditEventPage, AuditFilterParams } from '../types';
import { request } from './client';

export async function getAuditEvents(params?: AuditFilterParams): Promise<AuditEventPage> {
  return request<AuditEventPage>('/audit/events', {
    params: params as Record<string, string | number | undefined>,
  });
}

export async function getAuditEventDetail(eventId: string): Promise<AuditEvent> {
  return request<AuditEvent>(`/audit/events/${encodeURIComponent(eventId)}`);
}
