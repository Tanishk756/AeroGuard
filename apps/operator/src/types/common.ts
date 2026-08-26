export interface ApiError {
  error_code: string;
  message: string;
  correlation_id?: string;
  status: number;
}

export interface SystemHealthResponse {
  status: string;
  database: string;
}

export interface SystemInfoResponse {
  application: string;
  version: string;
  environment: string;
  python_version: string;
  platform: string;
  debug: boolean;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}
