"""RBAC management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import PermissionResponse, RoleAssignmentResponse, RoleCreate, RoleResponse, RoleUpdate
from app.services.rbac import assign_permission, assign_role, create_role, delete_role, revoke_permission, revoke_role, update_role
from app.services.audit import AuditService

router = APIRouter()


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_permission("roles.read"))):
    return db.scalars(select(Role).order_by(Role.name)).all()


@router.post("/roles", response_model=RoleResponse, status_code=201)
def add_role(payload: RoleCreate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.create"))):
    try:
        role = create_role(db, payload.name, payload.description)
        AuditService(db).record_event("ROLE_CREATED", "create_role", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="role", target_id=role.id)
        db.commit()
        db.refresh(role)
        return role
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Role mutation could not be completed") from exc
    except Exception:
        db.rollback()
        raise


@router.get("/roles/{role_id}", response_model=RoleResponse)
def get_role(role_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("roles.read"))):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def patch_role(role_id: str, payload: RoleUpdate, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.update"))):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    try:
        role = update_role(db, role, payload.description)
        AuditService(db).record_event("ROLE_UPDATED", "update_role", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="role", target_id=role.id)
        db.commit()
        db.refresh(role)
        return role
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.delete("/roles/{role_id}", status_code=204)
def remove_role(role_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.delete"))):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    try:
        delete_role(db, role)
        AuditService(db).record_event("ROLE_DELETED", "delete_role", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="role", target_id=role_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(db: Session = Depends(get_db), _: User = Depends(require_permission("permissions.read"))):
    return db.scalars(select(Permission).order_by(Permission.key)).all()


@router.post("/users/{user_id}/roles/{role_id}", response_model=RoleAssignmentResponse)
def add_user_role(user_id: str, role_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.assign"))):
    target = db.get(User, user_id)
    role = db.get(Role, role_id)
    if target is None or role is None:
        raise HTTPException(status_code=404, detail="User or role not found")
    try:
        assign_role(db, actor, target, role)
        AuditService(db).record_event("ROLE_ASSIGNED", "assign_role", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="user", target_id=target.id, metadata={"role_id": role.id})
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Role is already assigned") from exc
    except Exception:
        db.rollback()
        raise
    return RoleAssignmentResponse(user_id=target.id, role_id=role.id, role_name=role.name)


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
def remove_user_role(user_id: str, role_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.assign"))):
    target = db.get(User, user_id)
    role = db.get(Role, role_id)
    if target is None or role is None:
        raise HTTPException(status_code=404, detail="User or role not found")
    try:
        revoke_role(db, actor, target, role)
        AuditService(db).record_event("ROLE_REVOKED", "revoke_role", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="user", target_id=target.id, metadata={"role_id": role.id})
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=204)
def add_role_permission(role_id: str, permission_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.update"))):
    role = db.get(Role, role_id)
    permission = db.get(Permission, permission_id)
    if role is None or permission is None:
        raise HTTPException(status_code=404, detail="Role or permission not found")
    try:
        assign_permission(db, actor, role, permission)
        AuditService(db).record_event("PERMISSION_ASSIGNED", "assign_permission", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="role", target_id=role.id, permission=permission.key)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Permission is already assigned") from exc
    except Exception:
        db.rollback()
        raise


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204)
def remove_role_permission(role_id: str, permission_id: str, request: Request, db: Session = Depends(get_db), actor: User = Depends(require_permission("roles.update"))):
    role = db.get(Role, role_id)
    permission = db.get(Permission, permission_id)
    if role is None or permission is None:
        raise HTTPException(status_code=404, detail="Role or permission not found")
    try:
        revoke_permission(db, actor, role, permission)
        AuditService(db).record_event("PERMISSION_REVOKED", "revoke_permission", "SUCCESS", correlation=request.state.correlation_id, actor=actor, target_type="role", target_id=role.id, permission=permission.key)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise