from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sistema.app.core.config import settings
from sistema.app.services.time_utils import now_sgt
from sistema.app.services.transport_ai_llm_settings import (
    get_legacy_transport_ai_llm_settings,
    mask_transport_ai_api_key,
)


def build_session_factory(database_url: str):
    engine = sa.create_engine(database_url)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def export_legacy_transport_ai_llm_settings(
    db: Session,
    *,
    include_ciphertext: bool = True,
) -> dict[str, object]:
    persisted_settings = get_legacy_transport_ai_llm_settings(db)
    payload: dict[str, object] = {
        "exported_at": now_sgt().isoformat(),
        "legacy_settings_present": persisted_settings is not None,
        "settings": None,
    }
    if persisted_settings is None:
        return payload

    payload["settings"] = {
        "id": persisted_settings.id,
        "provider": persisted_settings.provider,
        "model_name": persisted_settings.model_name,
        "reasoning_effort": persisted_settings.reasoning_effort,
        "has_api_key": bool(persisted_settings.api_key_ciphertext),
        "api_key_hint": mask_transport_ai_api_key(api_key_last4=persisted_settings.api_key_last4),
        "api_key_last4": persisted_settings.api_key_last4,
        "api_key_ciphertext": persisted_settings.api_key_ciphertext if include_ciphertext else None,
        "updated_by_admin_id": persisted_settings.updated_by_admin_id,
        "created_at": persisted_settings.created_at.isoformat(),
        "updated_at": persisted_settings.updated_at.isoformat(),
    }
    return payload


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export the legacy singleton Transport AI LLM settings row so rollout can archive the old state "
            "before project-scoped backfill."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=settings.database_url,
        help="SQLAlchemy database URL. Defaults to the configured DATABASE_URL.",
    )
    parser.add_argument(
        "--output",
        help="Optional path where the JSON export should be written.",
    )
    parser.add_argument(
        "--redact-ciphertext",
        action="store_true",
        help="Omit the encrypted API key from the JSON payload when only a sanitized report is needed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    engine, session_factory = build_session_factory(args.database_url)
    try:
        with session_factory() as db:
            payload = export_legacy_transport_ai_llm_settings(
                db,
                include_ciphertext=not args.redact_ciphertext,
            )
    finally:
        engine.dispose()

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content)
    return 0 if payload["legacy_settings_present"] else 3


if __name__ == "__main__":
    raise SystemExit(main())