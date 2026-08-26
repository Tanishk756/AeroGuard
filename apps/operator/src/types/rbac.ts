export interface PermissionResponse {
  id: string;
  key: string;
  resource: string;
  action: string;
  description: string;
}

export interface RoleResponse {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  created_at: string;
  updated_at: string;
  permissions: PermissionResponse[];
}

export interface RoleCreate {
  name: string;
  description: string;
}

export interface RoleUpdate {
  description: string;
}

export interface RoleAssignmentResponse {
  user_id: string;
  role_id: string;
  role_name: string;
}

export type RbacRole = RoleResponse;
export type RbacPermission = PermissionResponse;
