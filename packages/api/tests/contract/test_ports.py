from typing import get_type_hints

from evox_api.ports import (
    EscalationPort,
    KnowledgePort,
    ModelGateway,
    OutcomeMemoryPort,
    PublicationPort,
    QaEvidencePort,
    QueueBoundary,
    WorkflowEngine,
)


def test_public_ports_are_explicit_protocol_boundaries() -> None:
    ports = (
        WorkflowEngine,
        ModelGateway,
        KnowledgePort,
        OutcomeMemoryPort,
        EscalationPort,
        PublicationPort,
        QaEvidencePort,
        QueueBoundary,
    )

    assert all(get_type_hints(port) == {} for port in ports)
    assert all(getattr(port, "_is_protocol") for port in ports)
