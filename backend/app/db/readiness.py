from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db import database


REQUIRED_TABLES = frozenset(
    {
        "users",
        "datasets",
        "dataset_columns",
        "query_requests",
        "audit_logs",
        "alembic_version",
    }
)


class DatabaseReadinessError(RuntimeError):
    pass


def _alembic_config() -> Config:
    return Config("alembic.ini")


def expected_migration_revision() -> str:
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    if head is None:
        raise DatabaseReadinessError("Database migration head could not be determined")
    return head


def run_startup_migrations() -> None:
    if settings.APP_ENV.lower() != "production":
        return

    command.upgrade(_alembic_config(), "head")


def verify_database_ready() -> None:
    try:
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            tables = set(inspect(connection).get_table_names())
            missing_tables = sorted(REQUIRED_TABLES - tables)
            if missing_tables:
                raise DatabaseReadinessError(
                    "Database schema is not ready; missing tables: "
                    + ", ".join(missing_tables)
                )

            result = connection.execute(text("SELECT version_num FROM alembic_version"))
            applied_revisions = {str(row[0]) for row in result if row[0]}
    except DatabaseReadinessError:
        raise
    except SQLAlchemyError as exc:
        raise DatabaseReadinessError("Database connection failed") from exc

    expected_revision = expected_migration_revision()
    if expected_revision not in applied_revisions:
        raise DatabaseReadinessError(
            f"Database migration is not current; expected {expected_revision}"
        )
