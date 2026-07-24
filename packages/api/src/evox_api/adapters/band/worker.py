"""Persistent Band worker composition entry point.

The deployment composition root supplies real repository and queue adapters.  This
module deliberately does not create substitutes when either dependency is absent.
"""

from __future__ import annotations

from pathlib import Path

from evox_api.adapters.band.escalation import (
    BandEscalationWorker,
    BandResponseProcessor,
    EscalationConfig,
    JobQueueEscalationResumer,
    SqliteEscalationStore,
)
from evox_api.ports.repositories import JobRepository, QueueBoundary


async def run_worker(*, database_path: Path, jobs: JobRepository, queue: QueueBoundary) -> None:
    """Connect Band's persistent WebSocket and correlate responses to real Jobs."""
    config = EscalationConfig.from_environment()
    store = SqliteEscalationStore(database_path)
    processor = BandResponseProcessor(
        config=config,
        store=store,
        resumer=JobQueueEscalationResumer(jobs=jobs, queue=queue),
    )
    await BandEscalationWorker(config=config, processor=processor).run_forever()
