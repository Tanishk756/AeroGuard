import { ApiError } from '../types';

export class AeroGuardApiError extends Error implements ApiError {
  error_code: string;
  correlation_id?: string;
  status: number;

  constructor(status: number, message: string, error_code = 'UNKNOWN_ERROR', correlation_id?: string) {
    super(message);
    this.name = 'AeroGuardApiError';
    this.status = status;
    this.error_code = error_code;
    this.correlation_id = correlation_id;
  }
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

const API_BASE = '/api/v1';

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers, ...customConfig } = options;

  let url = endpoint.startsWith('/') ? `${API_BASE}${endpoint}` : `${API_BASE}/${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    }
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const config: RequestInit = {
    method: 'GET',
    credentials: 'include', // Standard cookie inclusion for HttpOnly sessions
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    ...customConfig,
  };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      let errorCode = 'HTTP_ERROR';
      let message = response.statusText || `Request failed with status ${response.status}`;
      let correlationId: string | undefined;

      try {
        const errorData = await response.json();
        if (errorData) {
          errorCode = errorData.error_code || errorData.detail || errorCode;
          message = errorData.message || (typeof errorData.detail === 'string' ? errorData.detail : message);
          correlationId = errorData.correlation_id;
        }
      } catch {
        // Response was not JSON
      }

      throw new AeroGuardApiError(response.status, message, errorCode, correlationId);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json() as T;
  } catch (err: unknown) {
    if (err instanceof AeroGuardApiError) {
      throw err;
    }
    const message = err instanceof Error ? err.message : 'Network error: could not connect to backend';
    throw new AeroGuardApiError(0, message, 'NETWORK_ERROR');
  }
}
