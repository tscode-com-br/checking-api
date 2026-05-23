from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from sistema.app.database import Base
from sistema.app.models import Project, User, UserProjectMembership
from sistema.app.services.user_projects import (
    add_user_project_membership,
    assign_user_active_project,
    ensure_user_active_project_is_member,
    list_user_project_names,
    remove_user_project_membership,
    replace_user_project_memberships,
    resolve_user_active_project,
    user_belongs_to_project,
)


def _build_database_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path.as_posix()}"


def _build_session_factory(db_path: Path):
    engine = sa.create_engine(_build_database_url(db_path))
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def _create_project(session: Session, name: str) -> Project:
    project = Project(
        name=name,
        country_code="SG",
        country_name="Singapura",
        timezone_name="Asia/Singapore",
        address="Endereco Teste",
        zip_code="000000",
    )
    session.add(project)
    session.flush()
    return project


def _create_user(session: Session, *, chave: str, projeto: str) -> User:
    user = User(
        rfid=None,
        chave=chave,
        senha=None,
        perfil=0,
        admin_monitored_projects_json=None,
        nome=f"Usuario {chave}",
        projeto=projeto,
        workplace=None,
        vehicle_id=None,
        placa=None,
        end_rua=None,
        zip=None,
        email=None,
        local=None,
        checkin=None,
        time=None,
        last_active_at=sa.func.now(),
        inactivity_days=0,
    )
    session.add(user)
    session.flush()
    return user


def test_user_project_helpers_materialize_a_legacy_single_project_user(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_legacy.db")
    try:
        with session_factory() as session:
            _create_project(session, "P83")
            user = _create_user(session, chave="UP01", projeto="P83")

            assert list_user_project_names(session, user) == ["P83"]
            assert resolve_user_active_project(user, ["P83"]) == "P83"
            assert user_belongs_to_project(session, user, "p83") is True

            ensured_names = ensure_user_active_project_is_member(session, user)
            session.commit()

            membership_rows = session.execute(
                sa.select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
            ).scalars().all()

        assert ensured_names == ["P83"]
        assert len(membership_rows) == 1
        assert membership_rows[0].user_id == user.id
    finally:
        engine.dispose()


def test_user_project_helpers_preserve_active_project_while_adding_memberships(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_add.db")
    try:
        with session_factory() as session:
            _create_project(session, "P80")
            _create_project(session, "P83")
            _create_project(session, "P84")
            user = _create_user(session, chave="UP02", projeto="P83")

            added_names = add_user_project_membership(session, user, "P80")
            replaced_names = replace_user_project_memberships(session, user, ["P84", "P80", "P83"])
            session.commit()

        assert added_names == ["P80", "P83"]
        assert replaced_names == ["P80", "P83", "P84"]
        assert user.projeto == "P83"
    finally:
        engine.dispose()


def test_user_project_helpers_fallback_active_project_to_first_remaining_membership(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_remove.db")
    try:
        with session_factory() as session:
            _create_project(session, "P80")
            _create_project(session, "P83")
            user = _create_user(session, chave="UP03", projeto="P83")

            add_user_project_membership(session, user, "P80")
            remaining_names = remove_user_project_membership(session, user, "P83")
            session.commit()

            refreshed_user = session.get(User, user.id)

        assert remaining_names == ["P80"]
        assert refreshed_user is not None
        assert refreshed_user.projeto == "P80"
    finally:
        engine.dispose()


def test_user_project_helpers_assign_active_project_without_removing_other_memberships(tmp_path):
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_assign.db")
    try:
        with session_factory() as session:
            _create_project(session, "P80")
            _create_project(session, "P83")
            user = _create_user(session, chave="UP04", projeto="P83")

            add_user_project_membership(session, user, "P80")
            assigned_names = assign_user_active_project(session, user, "P80")
            session.commit()

            refreshed_user = session.get(User, user.id)

        assert assigned_names == ["P80", "P83"]
        assert refreshed_user is not None
        assert refreshed_user.projeto == "P80"
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# Migration 0067: usuario sem projeto vinculado e estado valido
# ---------------------------------------------------------------------------


def test_replace_memberships_accepts_empty_list_and_clears_projeto(tmp_path):
    """Apos migration 0067: lista vazia remove todas memberships e zera user.projeto."""
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_empty.db")
    try:
        with session_factory() as session:
            _create_project(session, "P80")
            _create_project(session, "P83")
            user = _create_user(session, chave="UP05", projeto="P83")

            replace_user_project_memberships(session, user, ["P80", "P83"])
            session.commit()

            remaining = replace_user_project_memberships(session, user, [])
            session.commit()

            refreshed_user = session.get(User, user.id)
            membership_rows = session.execute(
                sa.select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
            ).scalars().all()

        assert remaining == []
        assert membership_rows == []
        assert refreshed_user is not None
        assert refreshed_user.projeto is None
    finally:
        engine.dispose()


def test_resolve_active_project_returns_empty_when_no_memberships_and_no_legacy(tmp_path):
    """resolve_user_active_project nao levanta mais excecao quando user nao tem nada."""
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_resolve.db")
    try:
        with session_factory() as session:
            user = _create_user(session, chave="UP06", projeto="P83")
            user.projeto = None
            session.flush()
            session.commit()

        assert resolve_user_active_project(user, []) == ""
        assert resolve_user_active_project(user, None) == ""
    finally:
        engine.dispose()


def test_ensure_active_project_membership_returns_empty_for_user_without_projects(tmp_path):
    """ensure_user_active_project_is_member retorna lista vazia sem erro quando user nao tem projetos."""
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_ensure.db")
    try:
        with session_factory() as session:
            user = _create_user(session, chave="UP07", projeto="P83")
            user.projeto = None
            session.flush()
            session.commit()

            result = ensure_user_active_project_is_member(session, user)

        assert result == []
    finally:
        engine.dispose()


def test_remove_last_membership_keeps_user_without_projects(tmp_path):
    """remove_user_project_membership permite remover a ultima membership do usuario."""
    engine, session_factory = _build_session_factory(tmp_path / "user_projects_remove_last.db")
    try:
        with session_factory() as session:
            _create_project(session, "P80")
            user = _create_user(session, chave="UP08", projeto="P80")
            replace_user_project_memberships(session, user, ["P80"])
            session.commit()

            remaining = remove_user_project_membership(session, user, "P80")
            session.commit()

            refreshed_user = session.get(User, user.id)
            membership_rows = session.execute(
                sa.select(UserProjectMembership).where(UserProjectMembership.user_id == user.id)
            ).scalars().all()

        assert remaining == []
        assert membership_rows == []
        assert refreshed_user is not None
        assert refreshed_user.projeto is None
    finally:
        engine.dispose()