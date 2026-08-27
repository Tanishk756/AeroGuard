/**
 * Stage UI7 — Developer & API Console Type Definitions
 */

export type ApiDomain =
  | 'Platform & Health'
  | 'Authentication & Session'
  | 'Sensor Ingestion'
  | 'Tracking & Fusion'
  | 'Intelligence & Defense'
  | 'Simulation & Scenarios'
  | 'Historical & Analytics'
  | 'Governance & RBAC';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface ApiParamDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'enum';
  required: boolean;
  description: string;
  defaultValue?: string | number | boolean;
  options?: string[];
}

export interface ApiEndpoint {
  id: string;
  domain: ApiDomain;
  name: string;
  method: HttpMethod;
  path: string;
  description: string;
  requiredPermission?: string;
  requiredAnyPermissions?: string[];
  pathParams?: ApiParamDefinition[];
  queryParams?: ApiParamDefinition[];
  requestBodySchema?: string;
  requestBodyTemplate?: string;
  responseDescription?: string;
}

export interface DispatchedResponse {
  status: number;
  statusText: string;
  ok: boolean;
  headers: Record<string, string>;
  data: unknown;
  durationMs: number;
  correlationId?: string;
  error?: string;
}

export interface DetectionIngestPreset {
  id: string;
  name: string;
  source_type: 'RADAR' | 'RF' | 'OPTICAL';
  description: string;
  payload: {
    source_detection_id: string;
    timestamp: string;
    latitude: number;
    longitude: number;
    altitude_m: number;
    heading_deg?: number;
    speed_mps?: number;
    source_type: string;
    confidence: number;
    metadata: Record<string, unknown>;
  };
}

export interface DetectionValidationResult {
  valid: boolean;
  errors: string[];
}

export interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  description: string;
  constraints?: string;
  nestedFields?: SchemaField[];
  itemType?: string;
}

export interface SchemaDefinition {
  name: string;
  domain: ApiDomain;
  description: string;
  fields: SchemaField[];
}

export interface DetectionIngestionResult {
  detection_id: string;
  created: boolean;
  sensor_id: string;
  source_detection_id: string;
  timestamp: string;
}
