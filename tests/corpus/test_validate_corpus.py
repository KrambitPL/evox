"""Contract tests for the reviewed EvoAgentX issue corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_corpus import CorpusValidationError, load_optimizer_cases, validate_corpus

ROOT = Path(__file__).resolve().parents[2]


def test_corpus_is_valid_and_has_locked_split_counts() -> None:
    report = validate_corpus(ROOT / "corpus")

    assert report.split_counts == {"train": 8, "dev": 4, "heldout": 3}
    assert report.total_cases == 15


def test_schema_matches_the_validator_contract() -> None:
    schema = json.loads((ROOT / "corpus" / "schema.json").read_text())

    assert schema["additionalProperties"] is False
    assert "source_url" in schema["required"]


def test_optimizer_loader_cannot_load_heldout_cases() -> None:
    corpus = ROOT / "corpus"

    assert len(load_optimizer_cases(corpus, "train")) == 8
    assert len(load_optimizer_cases(corpus, "dev")) == 4
    with pytest.raises(CorpusValidationError, match="held-out"):
        load_optimizer_cases(corpus, "heldout")


def test_rejects_cross_split_issue_leakage(tmp_path: Path) -> None:
    source = ROOT / "corpus"
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for name in ("LOCK.json", "schema.json", "train.json", "heldout-manifest.json"):
        (corpus / name).write_text((source / name).read_text())
    dev = json.loads((source / "dev.json").read_text())
    dev[0] = json.loads((source / "train.json").read_text())[0]
    (corpus / "dev.json").write_text(json.dumps(dev))

    with pytest.raises(CorpusValidationError, match="appears in more than one split"):
        validate_corpus(corpus)


def test_rejects_non_issue_source_url(tmp_path: Path) -> None:
    corpus = ROOT / "corpus"
    case = json.loads((corpus / "train.json").read_text())[0]
    case["source_url"] = "https://github.com/EvoAgentX/EvoAgentX/pull/90"
    temporary = tmp_path / "corpus"
    temporary.mkdir()
    for name in ("LOCK.json", "schema.json"):
        (temporary / name).write_text((corpus / name).read_text())
    (temporary / "train.json").write_text(json.dumps([case] * 8))
    (temporary / "dev.json").write_text(json.dumps(json.loads((corpus / "dev.json").read_text())))
    (temporary / "heldout-manifest.json").write_text((corpus / "heldout-manifest.json").read_text())

    with pytest.raises(CorpusValidationError, match="invalid EvoAgentX issue URL"):
        validate_corpus(temporary)
