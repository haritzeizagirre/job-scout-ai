"""
CLI tool to promote a user to admin role.

Usage:
    python scripts/set_admin.py teacher@example.com
"""
import sys
import os

# Ensure we can import from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.db import get_user_by_email, set_user_role, init_db


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip()
    init_db()

    user = get_user_by_email(email)
    if not user:
        print(f"❌ No user found with email: {email}")
        print("   The user must register first via the web app.")
        sys.exit(1)

    set_user_role(email, "admin")
    print(f"✅ {email} has been promoted to admin.")
    print("   They now have unlimited scout runs.")


if __name__ == "__main__":
    main()
