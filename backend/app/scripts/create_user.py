import re
import getpass
from app.database import SessionLocal
from app.models.user import User
from app.routers.user_router import hash_password


def validate_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def main():
    print("====================================================")
    print("           NBD Platform User Creation Seeder         ")
    print("====================================================")

    db = SessionLocal()
    try:
        # 1. Prompt Email
        while True:
            email = input("Enter Email Address: ").strip()
            if not email:
                print("Email cannot be empty. Please try again.")
                continue
            if not validate_email(email):
                print("Invalid email format. Please try again.")
                continue

            # Check uniqueness
            exists = db.query(User).filter(User.email == email).first()
            if exists:
                print(f"User with email '{email}' already exists.")
                continue
            break

        # 2. Prompt Role
        valid_roles = ["Admin", "Reviewer", "Partner"]
        while True:
            print("Select Role:")
            for idx, r in enumerate(valid_roles, start=1):
                print(f"  {idx}. {r}")
            role_choice = input("Enter choice (1-3): ").strip()
            if role_choice in ("1", "2", "3"):
                role = valid_roles[int(role_choice) - 1]
                break
            else:
                print("Invalid choice. Please select 1, 2, or 3.")

        # 3. Prompt Organization
        organization = input(
            "Enter Organization (optional, press Enter to skip): "
        ).strip()
        if not organization:
            organization = None

        # 4. Prompt Password
        while True:
            password = getpass.getpass("Enter Password: ")
            if not password or len(password) < 6:
                print("Password must be at least 6 characters long.")
                continue

            confirm = getpass.getpass("Confirm Password: ")
            if password != confirm:
                print("Passwords do not match. Please try again.")
                continue
            break

        # 5. Create User
        pwd_hash = hash_password(password)
        new_user = User(
            email=email,
            role=role,
            organization=organization,
            password_hash=pwd_hash,
            is_active=True,
        )
        db.add(new_user)
        db.commit()

        print("\n====================================================")
        print("🎉 User created successfully!")
        print(f"  Email:        {email}")
        print(f"  Role:         {role}")
        print(f"  Organization: {organization or 'None'}")
        print("====================================================")

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
