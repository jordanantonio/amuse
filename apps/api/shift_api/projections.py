"""Restricted PostgreSQL projections contain no calendar labels or project titles."""

from types import SimpleNamespace

from sqlalchemy import text


def hosted(db):
    from .config import settings

    return not settings.demo_mode and db.get_bind().dialect.name == "postgresql"


def busy_windows(db):
    return [
        SimpleNamespace(**dict(row))
        for row in db.execute(text("SELECT * FROM public.shift_busy()")).mappings()
    ]


def external_commitments(db, project_id):
    return [
        SimpleNamespace(**dict(row))
        for row in db.execute(
            text("SELECT * FROM public.shift_external_commitments(:project)"),
            {"project": project_id},
        ).mappings()
    ]
