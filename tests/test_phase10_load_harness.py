from __future__ import annotations

import json
from pathlib import Path

from scripts.load.phase10_support import (
    GeneratedIdentityConfig,
    IdentityPool,
    Phase10Identity,
    build_web_registration_payload,
    build_web_submit_payload,
    generate_identities,
    load_phase10_harness_config,
)


def test_generate_identities_builds_four_character_keys() -> None:
    generated = generate_identities(
        GeneratedIdentityConfig(
            prefix="L",
            count=3,
            start_index=1,
            password="abc123",
            project="p80",
            name_prefix="Phase10",
            email_domain="load.invalid",
        )
    )

    assert [identity.chave for identity in generated] == ["L001", "L002", "L003"]
    assert all(identity.projeto == "P80" for identity in generated)


def test_load_phase10_harness_config_accepts_generated_users(tmp_path: Path) -> None:
    config_path = tmp_path / "phase10.json"
    config_path.write_text(
        json.dumps(
            {
                "wait_time": {"min_seconds": 0.1, "max_seconds": 0.4},
                "location": {
                    "latitude": 1.2,
                    "longitude": 103.6,
                    "accuracy_meters": 7,
                    "fallback_local": "Base Teste"
                },
                "generated_users": {
                    "prefix": "Z",
                    "count": 2,
                    "password": "abc123",
                    "project": "p80"
                },
                "web_check": {
                    "action_cycle": ["checkin", "checkout"],
                    "informe": "normal"
                }
            }
        ),
        encoding="utf-8",
    )

    harness_config = load_phase10_harness_config(config_path)

    assert harness_config.wait_time.min_seconds == 0.1
    assert harness_config.wait_time.max_seconds == 0.4
    assert harness_config.location.fallback_local == "Base Teste"
    assert [identity.chave for identity in harness_config.identities] == ["Z001", "Z002"]


def test_load_phase10_harness_config_accepts_admin_transport_and_forms_sections(tmp_path: Path) -> None:
    config_path = tmp_path / "phase10-extended.json"
    config_path.write_text(
        json.dumps(
            {
                "location": {
                    "latitude": 1.2,
                    "longitude": 103.6,
                    "accuracy_meters": 7,
                    "fallback_local": "Base Teste"
                },
                "generated_users": {
                    "prefix": "Y",
                    "count": 1,
                    "password": "abc123",
                    "project": "p80"
                },
                "admin": {"chave": "HR70", "senha": "eAcacdLe2"},
                "transport": {"chave": "HR70", "senha": "eAcacdLe2", "route_kind": "work_to_home"},
                "forms_backlog": {"ready_path": "/api/health/ready", "producer_action_cycle": ["checkout", "checkin"]}
            }
        ),
        encoding="utf-8",
    )

    harness_config = load_phase10_harness_config(config_path)

    assert harness_config.admin is not None
    assert harness_config.admin.credentials.chave == "HR70"
    assert harness_config.transport is not None
    assert harness_config.transport.route_kind == "work_to_home"
    assert harness_config.forms_backlog is not None
    assert harness_config.forms_backlog.producer_action_cycle == ("checkout", "checkin")


def test_identity_pool_cycles_without_dropping_identities() -> None:
    pool = IdentityPool(
        (
            Phase10Identity("A001", "abc123", "P80", "Alpha 1", "a001@load.invalid"),
            Phase10Identity("A002", "abc123", "P80", "Alpha 2", "a002@load.invalid"),
        )
    )

    assert pool.checkout().chave == "A001"
    assert pool.checkout().chave == "A002"
    assert pool.checkout().chave == "A001"


def test_submit_payload_contains_required_fields() -> None:
    identity = Phase10Identity("B001", "abc123", "P80", "Beta 1", "b001@load.invalid")
    payload = build_web_submit_payload(identity, action="checkin", informe="normal", local="Escritório Principal")

    assert payload["chave"] == "B001"
    assert payload["projeto"] == "P80"
    assert payload["action"] == "checkin"
    assert payload["informe"] == "normal"
    assert payload["local"] == "Escritório Principal"
    assert payload["client_event_id"].startswith("phase10-b001-")
    assert "T" in payload["event_time"]


def test_registration_payload_matches_web_contract() -> None:
    identity = Phase10Identity("C001", "abc123", "P80", "Carga 1", "c001@load.invalid")
    payload = build_web_registration_payload(identity)

    assert payload == {
        "chave": "C001",
        "nome": "Carga 1",
        "projeto": "P80",
        "email": "c001@load.invalid",
        "senha": "abc123",
        "confirmar_senha": "abc123",
    }