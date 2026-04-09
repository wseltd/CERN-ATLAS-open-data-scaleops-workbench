"""CLI seed runner: loads metadata and docs corpus and reports counts."""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the ATLAS workbench database with release metadata and docs."
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite database URL (default: $DATABASE_URL or sqlite:///./atlas_workbench.db)",
    )
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        default=False,
        help="Skip fetching documentation pages (metadata only)",
    )
    args = parser.parse_args()

    db_url = args.db_path or os.environ.get("DATABASE_URL", "sqlite:///./atlas_workbench.db")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from atlas_workbench.core import docs_seeder, metadata_seeder
    from atlas_workbench.db.models import Base

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        meta_counts = metadata_seeder.seed(session)
        print(
            f"Metadata seeded: {meta_counts.get('releases', 0)} releases, "
            f"{meta_counts.get('collections', 0)} collections, "
            f"{meta_counts.get('datasets', 0)} datasets."
        )

        if not args.skip_docs:
            docs_count = docs_seeder.seed(session)
            print(f"Docs seeded: {docs_count} pages.")
        else:
            print("Docs seeding skipped (--skip-docs).")

    print("Seed complete.")


if __name__ == "__main__":
    main()
