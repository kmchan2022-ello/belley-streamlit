# migrate_add_is_approver.py
from core.db import engine

def main():
    with engine.connect() as conn:
        conn.execute(
            "ALTER TABLE users ADD COLUMN is_approver INTEGER DEFAULT 0;"
        )
        conn.commit()

if __name__ == "__main__":
    main()
