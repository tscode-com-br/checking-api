from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Accident, AccidentUserReport, AccidentVideoUpload
from ..schemas import AccidentVideoLink, SituacaoPessoalRow


def _derive_display(
    report: AccidentUserReport,
    opened_at: datetime,
) -> tuple[str, str, str, int, int]:
    """Return (zone_display, status_display, row_color, priority, section)."""
    opened_at_cmp = opened_at.replace(tzinfo=None) if opened_at.tzinfo else opened_at

    # Priority 5 / Section 4: checked-out during this accident
    if (
        report.last_checkin_action == "check-out"
        and report.last_action_at is not None
        and report.last_action_at >= opened_at_cmp
    ):
        zone_display = (
            "Segurança"
            if report.zone == "safety"
            else ("Acidente" if report.zone == "accident" else "Aguardando")
        )
        status_display = (
            "OK"
            if report.status == "ok"
            else ("AJUDA" if report.status == "help" else "Aguardando")
        )
        return zone_display, status_display, "light-gray", 5, 4

    if report.zone == "accident" and report.status == "help":
        return "Acidente", "AJUDA", "blinking-red", 1, 1   # Seção 1: Emergência
    if report.zone == "accident" and report.status == "ok":
        return "Acidente", "OK", "yellow", 2, 2             # Seção 2: Local do Acidente
    if report.zone == "waiting":
        return "Aguardando", "Aguardando", "light-blue", 3, 3  # Seção 3: Não Reportados
    if report.zone == "safety" and report.status == "ok":
        return "Segurança", "OK", "light-green", 4, 4       # Seção 4: Demais
    return "Aguardando", "Aguardando", "light-blue", 3, 3   # fallback → seção 3


def build_situation_rows(
    db: Session,
    *,
    accident: Accident,
) -> list[SituacaoPessoalRow]:
    reports = (
        db.execute(
            select(AccidentUserReport).where(
                AccidentUserReport.accident_id == accident.id
            )
        )
        .scalars()
        .all()
    )

    rows: list[SituacaoPessoalRow] = []
    for report in reports:
        raw_videos = (
            db.execute(
                select(AccidentVideoUpload)
                .where(
                    AccidentVideoUpload.accident_id == accident.id,
                    AccidentVideoUpload.user_id == report.user_id,
                )
                .order_by(AccidentVideoUpload.captured_at.asc())
            )
            .scalars()
            .all()
        )
        videos = [
            AccidentVideoLink(
                video_id=v.id,
                public_url=v.public_url,
                captured_at=v.captured_at,
                content_type=v.content_type,
                size_bytes=v.size_bytes,
            )
            for v in raw_videos
        ]

        event_time = report.reported_at or report.last_action_at or report.created_at
        projects: list[str] = json.loads(report.user_projects_snapshot or "[]")
        zone_display, status_display, row_color, priority, section = _derive_display(
            report, accident.opened_at
        )

        # Derive "Atividade/Local" column
        if report.last_checkin_action and report.user_local_snapshot:
            action_label = "Check-In" if report.last_checkin_action == "check-in" else "Check-Out"
            activity_local: str | None = f"{action_label}/{report.user_local_snapshot}"
        elif report.user_local_snapshot:
            activity_local = report.user_local_snapshot
        else:
            activity_local = None

        rows.append(
            SituacaoPessoalRow(
                user_id=report.user_id,
                event_time=event_time,
                name=report.user_name_snapshot,
                chave=report.user_chave_snapshot,
                projects=projects,
                local=report.user_local_snapshot or None,
                activity_local=activity_local,
                zone=zone_display,
                status=status_display,
                phone=report.user_phone_snapshot,
                videos=videos,
                priority=priority,
                section=section,
                awareness_status=report.awareness_status,
                row_color=row_color,
            )
        )

    def _sort_key(row: SituacaoPessoalRow) -> tuple:
        if row.section == 4:
            acknowledged = 0 if row.awareness_status == "acknowledged" else 1
            has_checkin = 0 if (row.activity_local and "Check-In" in row.activity_local) else 1
            return (row.section, acknowledged, has_checkin, row.name)
        # Within sections 1-3: sort by section, then priority, then most-recent first
        return (row.section, row.priority, -row.event_time.timestamp(), row.name)

    rows.sort(key=_sort_key)
    return rows
