export interface User {
  id: string;
  username: string;
  display_name: string;
  email: string;
  status: 'ACTIVE' | 'DISABLED';
  roles: string[];
  permissions: string[];
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
}

export interface CurrentUserResponse {
  id: string;
  username: string;
  display_name: string;
  email: string;
  status: 'ACTIVE' | 'DISABLED';
  roles: string[];
  permissions: string[];
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
}

export interface Permission {
  id: string;
  name: string;
  description: string;
}
