from inspect import signature
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
from evox_api.ports.sponsors import KnowledgeCitation, KnowledgeResult


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


def test_knowledge_results_preserve_senso_source_freshness_and_tenant_context() -> None:
    annotations = KnowledgeCitation.__annotations__

    assert {"source_uri", "source_title", "retrieved_at", "tenant_id"} <= set(annotations)
    assert "citations" in KnowledgeResult.__annotations__


def test_tenant_scoped_knowledge_and_memory_ports_require_filters() -> None:
    knowledge_parameters = signature(KnowledgePort.retrieve).parameters
    memory_parameters = signature(OutcomeMemoryPort.recall).parameters

    assert {"tenant_id", "filters"} <= set(knowledge_parameters)
    assert {"tenant_id", "filters"} <= set(memory_parameters)
