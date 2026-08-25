"""Server-side permission evaluation."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


class AuthorizationService:
    def __init__(self, db: Session):
        self.db = db

    def permission_keys(self, user: User) -> set[str]:
        statement = (
            select(Permission.key)
            .join(Role.permissions)
            .join(Role.users)
            .where(User.id == user.id)
        )
        return set(self.db.scalars(statement).all())

    def has_permission(self, user: User, permission_key: str) -> bool:
        return permission_key in self.permission_keys(user)

    def has_any_permission(self, user: User, permission_keys: Iterable[str]) -> bool:
        return bool(self.permission_keys(user).intersection(permission_keys))

    def has_all_permissions(self, user: User, permission_keys: Iterable[str]) -> bool:
        return set(permission_keys).issubset(self.permission_keys(user))