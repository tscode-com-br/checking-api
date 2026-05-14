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
) -> tuple[str, str, str, int]:
    """Return (zone_display, status_display, row_color, priority)."""
    # Normalise opened_at for comparison: strip tz if report datetimes are naive
    opened_at_cmp = opened_at.replace(tzinfo=None) if opened_at.tzinfo else opened_at

    # Priority 5: user checked-out during this accident
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
        return zone_display, status_display, "light-gray", 5

    if report.zone == "accident" and report.status == "help":
        return "Acidente", "AJUDA", "blinking-red", 1
    if report.zone == "accident" and report.status == "ok":
        return "Acidente", "OK", "yellow", 2
    if report.zone == "waiting":
        return "Aguardando", "Aguardando", "turquoise", 3
    if report.zone == "safety" and report.status == "ok":
        return "Segurança", "OK", "light-green", 4
    return "Aguardando", "Aguardando", "white", 3


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
        # Gather associated videos ordered by captured_at ASC
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
        zone_display, status_display, row_color, priority = _derive_display(
            report, accident.opened_at
        )

        rows.append(
            SituacaoPessoalRow(
                user_id=report.user_id,
                event_time=event_time,
                name=report.user_name_snapshot,
                chave=report.user_chave_snapshot,
                projects=projects,
                local=report.user_local_snapshot or None,
                zone=zone_display,
                status=status_display,
                phone=report.user_phone_snapshot,
                videos=videos,
                priority=priority,
                row_color=row_color,
            )
        )

    rows.sort(key=lambda r: (r.priority, -r.event_time.timestamp()))
    return rows
