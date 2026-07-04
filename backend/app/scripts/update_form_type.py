import os
import sys

# Add backend app directory to python path
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)

from app.database import SessionLocal  # noqa
from app.models.form import Form, FormType, FormStatus  # noqa


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print(" 🌊 Nile Basin Wetland Platform - Form Settings Editor")
        print("=" * 60)

        # Get list of forms
        forms = db.query(Form).order_by(Form.id.asc()).all()
        if not forms:
            print("No forms found in the database.")
            return

        print("\nAvailable Forms:")
        for f in forms:
            # Map form type enum label
            try:
                type_label = FormType(f.type).name
            except ValueError:
                type_label = f"Unknown ({f.type})"

            try:
                status_label = FormStatus(f.status).name
            except ValueError:
                status_label = f"Unknown ({f.status})"

            print(f"{f.id}) Name: {f.name}")
            print(f"   UID: {f.kobo_asset_id or 'No Kobo UID'}")
            print(f"   Type: {type_label} | Status: {status_label}")
            print("-" * 60)

        # 1. Select Form
        choice = input("\nEnter Form ID to edit (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            return

        try:
            form_id = int(choice)
        except ValueError:
            print("Invalid input. Please enter a valid Form ID.")
            return

        selected_form = db.query(Form).filter(Form.id == form_id).first()
        if not selected_form:
            print(f"Form with ID {form_id} not found.")
            return

        print(f"\nEditing Form: '{selected_form.name}'")
        print("Leave empty to keep current value.")

        # 2. Edit Name
        new_name = input(f"New Name [{selected_form.name}]: ").strip()
        if new_name:
            selected_form.name = new_name

        # 3. Edit Type
        print("\nAvailable Form Types:")
        for t in FormType:
            print(f"  {t.value}) {t.name}")
        new_type = input(f"New Type [{selected_form.type}]: ").strip()
        if new_type:
            try:
                selected_form.type = int(new_type)
            except ValueError:
                print("Invalid type choice. Skipping type update.")

        # 4. Edit Status
        print("\nAvailable Form Statuses:")
        for s in FormStatus:
            print(f"  {s.value}) {s.name}")
        new_status = input(f"New Status [{selected_form.status}]: ").strip()
        if new_status:
            try:
                selected_form.status = int(new_status)
            except ValueError:
                print("Invalid status choice. Skipping status update.")

        # Save changes
        db.commit()
        print("\n🎉 Form updated successfully in the database!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
