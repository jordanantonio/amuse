from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    engine = create_engine(
        url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session


@event.listens_for(Session, "after_begin")
def set_identity(session, transaction, connection):
    if connection.dialect.name == "postgresql":
        from sqlalchemy import text

        connection.execute(
            text("SELECT set_config('shift.subject', :subject, true)"),
            {"subject": session.info.get("auth_subject", "")},
        )


def check_runtime_role():
    """Reject elevated credentials and unmigrated/unprotected hosted databases."""
    from sqlalchemy import text

    with engine.connect() as connection:
        safe = connection.scalar(
            text("""
            SELECT NOT (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole OR r.rolcreatedb OR r.rolreplication)
              AND pg_has_role(current_user, 'shift_app', 'member')
              AND NOT EXISTS (
                SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public' AND c.relkind='r' AND c.relname=ANY(:tables)
                  AND (pg_has_role(current_user, c.relowner, 'member') OR NOT c.relrowsecurity)
              )
              AND (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                   WHERE n.nspname='public' AND c.relkind='r' AND c.relname=ANY(:tables)) = :table_count
              AND EXISTS (SELECT 1 FROM pg_constraint WHERE conname='assignments_no_confirmed_overlap'
                          AND conrelid='public.assignments'::regclass AND contype='x')
              AND NOT has_schema_privilege(current_user, 'public', 'CREATE')
              AND NOT pg_has_role(current_user, 'pg_read_all_data', 'member')
              AND NOT pg_has_role(current_user, 'pg_write_all_data', 'member')
            FROM pg_roles r WHERE r.rolname=current_user
        """),
            {"tables": list(Base.metadata.tables), "table_count": len(Base.metadata.tables)},
        )
        if not safe:
            raise RuntimeError(
                "Hosted database requires migrated RLS and restricted shift_app credentials"
            )
