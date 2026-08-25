"""Explicit developer-only account initialization commands."""

from getpass import getpass

from app.database.session import SessionLocal
from app.services.auth import create_user


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


if __name__ == "__main__":
    import sys

    if sys.argv[1:] != ["create-user"]:
        raise SystemExit("Usage: python -m app.cli create-user")
    create_user_interactively()