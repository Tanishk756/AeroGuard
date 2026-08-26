import { PermissionResponse, RoleAssignmentResponse, RoleCreate, RoleResponse, RoleUpdate } from '../types';
import { request } from './client';

export async function getRoles(): Promise<RoleResponse[]> {
  return request<RoleResponse[]>('/roles');
}

export async function getRoleDetail(roleId: string): Promise<RoleResponse> {
  return request<RoleResponse>(`/roles/${encodeURIComponent(roleId)}`);
}

export async function createRole(data: RoleCreate): Promise<RoleResponse> {
  return request<RoleResponse>('/roles', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateRole(roleId: string, data: RoleUpdate): Promise<RoleResponse> {
  return request<RoleResponse>(`/roles/${encodeURIComponent(roleId)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteRole(roleId: string): Promise<void> {
  return request<void>(`/roles/${encodeURIComponent(roleId)}`, {
    method: 'DELETE',
  });
}

export async function getPermissions(): Promise<PermissionResponse[]> {
  return request<PermissionResponse[]>('/permissions');
}

export async function assignUserRole(userId: string, roleId: string): Promise<RoleAssignmentResponse> {
  return request<RoleAssignmentResponse>(`/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleId)}`, {
    method: 'POST',
  });
}

export async function revokeUserRole(userId: string, roleId: string): Promise<void> {
  return request<void>(`/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(roleId)}`, {
    method: 'DELETE',
  });
}

export async function assignRolePermission(roleId: string, permissionId: string): Promise<void> {
  return request<void>(`/roles/${encodeURIComponent(roleId)}/permissions/${encodeURIComponent(permissionId)}`, {
    method: 'POST',
  });
}

export async function revokeRolePermission(roleId: string, permissionId: string): Promise<void> {
  return request<void>(`/roles/${encodeURIComponent(roleId)}/permissions/${encodeURIComponent(permissionId)}`, {
    method: 'DELETE',
  });
}
