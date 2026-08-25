"""Explicit developer-only account initialization commands."""

from getpass import getpass

from app.database.session import SessionLocal
from app.services.auth import create_user
from app.services.rbac import bootstrap_super_admin, seed_rbac


def create_user_interactively() -> None:
    username = input("Username: ").strip()
    display_name = input("Display name: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password: ")
    password_confirmation = getpass("Confirm password: ")
    if password != password_confirmation:
        raise SystemExit("Passwords do not match.")
    with SessionLocal() as db:
        user = create_user(db, username, display_name, email, password)
    print(f"Created user {user.username}.")


def seed_rbac_data() -> None:
    with SessionLocal() as db:
        seed_rbac(db)
        db.commit()
    print("RBAC seed data is ready.")


def bootstrap_rbac_interactively() -> None:
    username = input("Existing active username: ").strip()
    confirmation = input("Type BOOTSTRAP to grant SUPER_ADMIN: ").strip()
    with SessionLocal() as db:
        user = bootstrap_super_admin(db, username, confirmation == "BOOTSTRAP")
        db.commit()
    print(f"Granted SUPER_ADMIN to {user.username}.")


if __name__ == "__main__":
    import sys

    commands = {
        "create-user": create_user_interactively,
        "seed-rbac": seed_rbac_data,
        "bootstrap-rbac": bootstrap_rbac_interactively,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        raise SystemExit("Usage: python -m app.cli create-user|seed-rbac|bootstrap-rbac")
    commands[sys.argv[1]]()