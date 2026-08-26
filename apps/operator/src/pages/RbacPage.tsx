import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  assignRolePermission,
  assignUserRole,
  createRole,
  deleteRole,
  getPermissions,
  getRoles,
  revokeRolePermission,
  revokeUserRole,
  updateRole,
} from '../api/rbac';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { PermissionResponse, RoleResponse } from '../types';

type RbacTab = 'roles' | 'permissions' | 'assignments';

export const RbacPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canCreateRole = hasPermission('roles.create');
  const canUpdateRole = hasPermission('roles.update');
  const canDeleteRole = hasPermission('roles.delete');
  const canAssignRole = hasPermission('roles.assign');

  const [activeTab, setActiveTab] = useState<RbacTab>('roles');
  const [roles, setRoles] = useState<RoleResponse[]>([]);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleResponse | null>(null);

  // Create role form state
  const [isCreatingRole, setIsCreatingRole] = useState<boolean>(false);
  const [newRoleName, setNewRoleName] = useState<string>('');
  const [newRoleDesc, setNewRoleDesc] = useState<string>('');
  const [editDesc, setEditDesc] = useState<string>('');
  const [isEditingDesc, setIsEditingDesc] = useState<boolean>(false);

  // User assignment state
  const [targetUserId, setTargetUserId] = useState<string>('');
  const [selectedAssignRoleId, setSelectedAssignRoleId] = useState<string>('');
  const [assignmentAction, setAssignmentAction] = useState<'assign' | 'revoke'>('assign');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isActionPending, setIsActionPending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const fetchRbacData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [rolesData, permsData] = await Promise.all([
        getRoles().catch(() => []),
        getPermissions().catch(() => []),
      ]);
      setRoles(rolesData);
      setPermissions(permsData);

      if (rolesData.length > 0) {
        if (!selectedRole) {
          setSelectedRole(rolesData[0]);
          setEditDesc(rolesData[0].description || '');
        } else {
          const updated = rolesData.find((r) => r.id === selectedRole.id);
          if (updated) {
            setSelectedRole(updated);
            setEditDesc(updated.description || '');
          }
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch RBAC data');
    } finally {
      setIsLoading(false);
    }
  }, [selectedRole]);

  useEffect(() => {
    fetchRbacData();
  }, [fetchRbacData]);

  // Group permissions by resource domain
  const permissionsByDomain = useMemo(() => {
    const map: Record<string, PermissionResponse[]> = {};
    for (const p of permissions) {
      const domain = p.resource || p.key.split('.')[0] || 'general';
      if (!map[domain]) map[domain] = [];
      map[domain].push(p);
    }
    return map;
  }, [permissions]);

  // Create custom role handler
  const handleCreateRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRoleName.trim() || !newRoleDesc.trim()) return;

    // Validate uppercase format ^[A-Z][A-Z0-9_]+$
    const validFormat = /^[A-Z][A-Z0-9_]+$/.test(newRoleName.trim());
    if (!validFormat) {
      setError('Role name must start with an uppercase letter and contain only uppercase letters, numbers, and underscores (e.g. TACTICAL_ANALYST).');
      return;
    }

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const created = await createRole({
        name: newRoleName.trim(),
        description: newRoleDesc.trim(),
      });
      setSuccessMessage(`Role '${created.name}' created successfully.`);
      setIsCreatingRole(false);
      setNewRoleName('');
      setNewRoleDesc('');
      await fetchRbacData();
      setSelectedRole(created);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create role');
    } finally {
      setIsActionPending(false);
    }
  };

  // Update role description handler
  const handleUpdateDescription = async () => {
    if (!selectedRole || selectedRole.is_system) return;
    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await updateRole(selectedRole.id, {
        description: editDesc.trim(),
      });
      setSuccessMessage(`Role description updated.`);
      setIsEditingDesc(false);
      await fetchRbacData();
      setSelectedRole(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update role description');
    } finally {
      setIsActionPending(false);
    }
  };

  // Delete custom role handler
  const handleDeleteRole = async (role: RoleResponse) => {
    if (role.is_system) return;
    if (!window.confirm(`Are you sure you want to permanently delete custom role '${role.name}'?`)) return;

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await deleteRole(role.id);
      setSuccessMessage(`Role '${role.name}' deleted successfully.`);
      setSelectedRole(null);
      await fetchRbacData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete role');
    } finally {
      setIsActionPending(false);
    }
  };

  // Toggle permission assignment on role
  const handleTogglePermission = async (perm: PermissionResponse) => {
    if (!selectedRole || selectedRole.is_system || !canUpdateRole) return;

    const assignedIds = new Set((selectedRole.permissions || []).map((p: PermissionResponse) => p.id));
    const isCurrentlyAssigned = assignedIds.has(perm.id);

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      if (isCurrentlyAssigned) {
        await revokeRolePermission(selectedRole.id, perm.id);
        setSuccessMessage(`Permission '${perm.key}' revoked from role '${selectedRole.name}'.`);
      } else {
        await assignRolePermission(selectedRole.id, perm.id);
        setSuccessMessage(`Permission '${perm.key}' granted to role '${selectedRole.name}'.`);
      }
      await fetchRbacData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update permission assignment');
    } finally {
      setIsActionPending(false);
    }
  };

  // User role assignment/revocation handler
  const handleUserRoleAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUserId.trim() || !selectedAssignRoleId) {
      setError('Please provide both a valid Target User ID and select a Role.');
      return;
    }

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);
    try {
      if (assignmentAction === 'assign') {
        const res = await assignUserRole(targetUserId.trim(), selectedAssignRoleId);
        setSuccessMessage(`Successfully assigned role '${res.role_name}' to user ID '${targetUserId}'.`);
      } else {
        await revokeUserRole(targetUserId.trim(), selectedAssignRoleId);
        setSuccessMessage(`Successfully revoked role from user ID '${targetUserId}'.`);
      }
      setTargetUserId('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Failed to ${assignmentAction} role for user`);
    } finally {
      setIsActionPending(false);
    }
  };

  const selectedRolePermIds = useMemo(() => {
    return new Set((selectedRole?.permissions || []).map((p) => p.id));
  }, [selectedRole]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-warning)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              RBAC Role & Access Governance (Stage D Engine)
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Deterministic role-permission mapping, custom security roles, and user authority administration.
          </p>
        </div>

        {/* View Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <Button
            variant={activeTab === 'roles' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('roles')}
            style={{ padding: '4px 10px', fontSize: '11px' }}
          >
            Roles & Matrix ({roles.length})
          </Button>
          <Button
            variant={activeTab === 'assignments' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('assignments')}
            style={{ padding: '4px 10px', fontSize: '11px' }}
          >
            User Role Assignment
          </Button>
          <Button
            variant={activeTab === 'permissions' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('permissions')}
            style={{ padding: '4px 10px', fontSize: '11px' }}
          >
            Permission Dictionary ({permissions.length})
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {successMessage && (
        <div
          style={{
            padding: '6px 10px',
            backgroundColor: 'var(--status-success-bg)',
            border: '1px solid var(--status-success-border)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span className="font-mono text-xs" style={{ color: 'var(--status-success)', fontWeight: 600 }}>
            ✓ {successMessage}
          </span>
          <Button variant="ghost" size="sm" onClick={() => setSuccessMessage(null)} style={{ padding: '0 4px', fontSize: '10px' }}>
            ✕
          </Button>
        </div>
      )}

      {/* Tab Content */}
      {activeTab === 'roles' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(420px, 1.6fr)', gap: 'var(--space-md)' }}>
          {/* Roles Directory List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <Card
              title="Registered Roles Directory"
              badge={<span className="font-mono text-xs text-muted">TOTAL: {roles.length}</span>}
              actions={
                canCreateRole && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setIsCreatingRole((prev) => !prev)}
                    style={{ padding: '2px 8px', fontSize: '11px' }}
                  >
                    {isCreatingRole ? 'Cancel' : '+ New Custom Role'}
                  </Button>
                )
              }
              bodyStyle={{ padding: 0 }}
            >
              {isLoading && roles.length === 0 ? (
                <LoadingState message="Loading RBAC roles..." />
              ) : roles.length === 0 ? (
                <EmptyState title="No Roles Found" description="No roles registered in database." />
              ) : (
                <div className="tactical-table-wrapper" style={{ maxHeight: '480px' }}>
                  <table className="tactical-table">
                    <thead>
                      <tr>
                        <th>Role Name</th>
                        <th>Type</th>
                        <th>Permissions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {roles.map((r) => {
                        const isSelected = selectedRole?.id === r.id;
                        return (
                          <tr
                            key={r.id}
                            onClick={() => {
                              setSelectedRole(r);
                              setEditDesc(r.description || '');
                              setIsEditingDesc(false);
                            }}
                            style={{
                              cursor: 'pointer',
                              backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                            }}
                          >
                            <td>
                              <div className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                                {r.name}
                              </div>
                              <div className="text-muted text-xs" style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {r.description}
                              </div>
                            </td>
                            <td>
                              <StatusBadge
                                status={r.is_system ? 'ACTIVE' : 'WARNING'}
                                label={r.is_system ? 'SYSTEM' : 'CUSTOM'}
                              />
                            </td>
                            <td className="font-mono text-xs text-muted">
                              {(r.permissions || []).length} perms
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Custom Role Creation Form */}
            {isCreatingRole && (
              <Card title="Create New Custom Role">
                <form onSubmit={handleCreateRole} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Role Name (Uppercase & Underscores)</label>
                    <input
                      type="text"
                      className="tactical-input font-mono"
                      value={newRoleName}
                      onChange={(e) => setNewRoleName(e.target.value.toUpperCase())}
                      placeholder="e.g. MISSION_SUPERVISOR"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Description</label>
                    <textarea
                      className="tactical-input font-mono"
                      value={newRoleDesc}
                      onChange={(e) => setNewRoleDesc(e.target.value)}
                      placeholder="Describe operational responsibilities..."
                      rows={2}
                      required
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-xs)', marginTop: '4px' }}>
                    <Button variant="ghost" size="sm" onClick={() => setIsCreatingRole(false)} disabled={isActionPending}>
                      Cancel
                    </Button>
                    <Button variant="primary" size="sm" type="submit" isLoading={isActionPending}>
                      Create Role
                    </Button>
                  </div>
                </form>
              </Card>
            )}
          </div>

          {/* Selected Role Permission Matrix & Details */}
          {selectedRole ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              {/* Role Header */}
              <Card
                title={`Role Configuration: ${selectedRole.name}`}
                badge={
                  <StatusBadge
                    status={selectedRole.is_system ? 'ACTIVE' : 'WARNING'}
                    label={selectedRole.is_system ? 'IMMUTABLE SYSTEM ROLE' : 'CUSTOM ROLE'}
                  />
                }
                actions={
                  !selectedRole.is_system && canDeleteRole && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDeleteRole(selectedRole)}
                      disabled={isActionPending}
                      style={{ padding: '2px 8px', fontSize: '11px' }}
                    >
                      Delete Custom Role
                    </Button>
                  )
                }
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                    <div className="kv-row">
                      <span className="kv-key">Role ID</span>
                      <span className="kv-value font-mono text-xs text-muted">{selectedRole.id}</span>
                    </div>
                    <div className="kv-row">
                      <span className="kv-key">Assigned Permissions</span>
                      <span className="kv-value font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                        {(selectedRole.permissions || []).length} / {permissions.length}
                      </span>
                    </div>
                  </div>

                  {/* Description Editor */}
                  <div>
                    <span className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                      Description
                    </span>
                    {isEditingDesc ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <textarea
                          className="tactical-input font-mono"
                          value={editDesc}
                          onChange={(e) => setEditDesc(e.target.value)}
                          rows={2}
                        />
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px' }}>
                          <Button variant="ghost" size="sm" onClick={() => setIsEditingDesc(false)}>Cancel</Button>
                          <Button variant="primary" size="sm" onClick={handleUpdateDescription} isLoading={isActionPending}>Save</Button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: 'var(--radius-sm)' }}>
                        <span className="font-mono text-xs">{selectedRole.description || 'No description provided.'}</span>
                        {!selectedRole.is_system && canUpdateRole && (
                          <Button variant="ghost" size="sm" onClick={() => setIsEditingDesc(true)} style={{ padding: '1px 6px', fontSize: '10px' }}>
                            Edit
                          </Button>
                        )}
                      </div>
                    )}
                  </div>

                  {selectedRole.is_system && (
                    <div style={{ padding: '4px 8px', backgroundColor: 'var(--bg-canvas)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
                      <p className="font-mono text-muted" style={{ margin: 0, fontSize: '10px' }}>
                        🔒 System-reserved roles are protected and cannot be deleted or re-configured to preserve platform stability and access safety.
                      </p>
                    </div>
                  )}
                </div>
              </Card>

              {/* Permission Assignment Matrix */}
              <Card title="Permission Grant Matrix" badge={<span className="font-mono text-xs text-muted">{permissions.length} TOTAL PERMISSIONS</span>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', maxHeight: '420px', overflowY: 'auto' }}>
                  {Object.entries(permissionsByDomain).map(([domain, perms]) => (
                    <div key={domain} style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', padding: '6px' }}>
                      <div className="font-mono text-xs uppercase-tracking" style={{ fontWeight: 700, color: 'var(--color-accent)', marginBottom: '4px' }}>
                        {domain.toUpperCase()} DOMAIN ({perms.length})
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '4px' }}>
                        {perms.map((p) => {
                          const isAssigned = selectedRolePermIds.has(p.id);
                          return (
                            <div
                              key={p.id}
                              onClick={() => !selectedRole.is_system && canUpdateRole && handleTogglePermission(p)}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '4px 8px',
                                backgroundColor: isAssigned ? 'var(--bg-surface-active)' : 'var(--bg-canvas)',
                                border: isAssigned ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: !selectedRole.is_system && canUpdateRole ? 'pointer' : 'default',
                                opacity: selectedRole.is_system ? 0.85 : 1,
                              }}
                              title={p.description}
                            >
                              <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span className="font-mono text-xs" style={{ fontWeight: isAssigned ? 600 : 400, color: isAssigned ? 'var(--color-accent)' : 'var(--text-secondary)' }}>
                                  {p.key}
                                </span>
                                <span className="text-muted" style={{ fontSize: '9px' }}>{p.action}</span>
                              </div>
                              <span style={{ fontSize: '12px' }}>
                                {isAssigned ? '✓' : '+'}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          ) : (
            <Card title="Role Inspection">
              <EmptyState title="No Role Selected" description="Select any role from the directory to inspect its permission matrix." />
            </Card>
          )}
        </div>
      )}

      {/* Tab: User Role Assignment */}
      {activeTab === 'assignments' && (
        <Card title="User Role Assignment & Membership Administration">
          <div style={{ maxWidth: '600px', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div
              style={{
                padding: '8px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <p className="font-mono text-muted text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
                ℹ <strong>User Discovery Notice</strong>: In compliance with AeroGuard security architecture, user accounts are authenticated via enterprise server sessions without exposing unauthenticated user lists. Enter the target User ID to assign or revoke role memberships.
              </p>
            </div>

            <form onSubmit={handleUserRoleAction} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              <div>
                <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                  Target User ID (UUID / Identifier)
                </label>
                <input
                  type="text"
                  className="tactical-input font-mono"
                  value={targetUserId}
                  onChange={(e) => setTargetUserId(e.target.value)}
                  placeholder="e.g. 1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
                  required
                />
              </div>

              <div>
                <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                  Select Role
                </label>
                <select
                  className="tactical-select font-mono"
                  value={selectedAssignRoleId}
                  onChange={(e) => setSelectedAssignRoleId(e.target.value)}
                  required
                >
                  <option value="">-- Choose Role --</option>
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} {r.is_system ? '(System)' : '(Custom)'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                  Operation Action
                </label>
                <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: 'var(--text-xs)' }}>
                    <input
                      type="radio"
                      name="action"
                      checked={assignmentAction === 'assign'}
                      onChange={() => setAssignmentAction('assign')}
                    />
                    Assign Role to User
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: 'var(--text-xs)' }}>
                    <input
                      type="radio"
                      name="action"
                      checked={assignmentAction === 'revoke'}
                      onChange={() => setAssignmentAction('revoke')}
                    />
                    Revoke Role from User
                  </label>
                </div>
              </div>

              <div style={{ marginTop: 'var(--space-xs)' }}>
                <Button
                  variant={assignmentAction === 'assign' ? 'primary' : 'danger'}
                  size="sm"
                  type="submit"
                  disabled={!canAssignRole || isActionPending}
                  isLoading={isActionPending}
                >
                  {assignmentAction === 'assign' ? 'Execute Role Assignment' : 'Execute Role Revocation'}
                </Button>
              </div>
            </form>
          </div>
        </Card>
      )}

      {/* Tab: Permission Dictionary */}
      {activeTab === 'permissions' && (
        <Card
          title="Granular Permission Dictionary"
          badge={<span className="font-mono text-xs text-muted">TOTAL: {permissions.length}</span>}
          bodyStyle={{ padding: 0 }}
        >
          <div className="tactical-table-wrapper" style={{ maxHeight: '560px' }}>
            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Permission Key</th>
                  <th>Domain / Resource</th>
                  <th>Action</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {permissions.map((p) => (
                  <tr key={p.id}>
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                      {p.key}
                    </td>
                    <td className="uppercase-tracking text-xs font-mono">{p.resource}</td>
                    <td className="font-mono text-xs text-muted">{p.action}</td>
                    <td style={{ color: 'var(--text-primary)' }}>{p.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
