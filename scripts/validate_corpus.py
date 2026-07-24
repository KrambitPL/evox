"""Validate the locked, provenance-rich EvoAgentX issue evaluation corpus."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ISSUE_URL = re.compile(r"^https://github\.com/EvoAgentX/EvoAgentX/issues/(\d+)$")
REQUIRED_CASE_FIELDS = {
    "id",
    "source_issue_number",
    "source_url",
    "closed_at",
    "title",
    "source_excerpt",
    "expected_disposition",
    "required_facts",
    "acceptable_citations",
    "escalation_behavior",
}
OPTIMIZER_SPLITS = frozenset({"train", "dev"})


class CorpusValidationError(ValueError):
    """Raised when a corpus lock, schema, provenance, or split invariant is broken."""


@dataclass(frozen=True)
class CorpusReport:
    total_cases: int
    split_counts: dict[str, int]


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CorpusValidationError(f"cannot read {path}: {error}") from error


def _valid_https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate_case(case: object, split: str) -> None:
    if not isinstance(case, dict):
        raise CorpusValidationError(f"{split} contains a non-object case")
    missing = REQUIRED_CASE_FIELDS - case.keys()
    if missing:
        raise CorpusValidationError(
            f"{case.get('id', split)} misses schema fields: {sorted(missing)}"
        )
    if not isinstance(case["id"], str) or not case["id"].startswith("evoagentx-"):
        raise CorpusValidationError("case id must be an evoagentx issue id")
    if not isinstance(case["source_issue_number"], int):
        raise CorpusValidationError(f"{case['id']} has a non-integer issue number")
    match = ISSUE_URL.fullmatch(str(case["source_url"]))
    if match is None or int(match.group(1)) != case["source_issue_number"]:
        raise CorpusValidationError(f"{case['id']} has an invalid EvoAgentX issue URL")
    if case["id"] != f"evoagentx-{case['source_issue_number']}":
        raise CorpusValidationError(f"{case['id']} does not match its source issue number")
    text_fields = (
        "closed_at",
        "title",
        "source_excerpt",
        "expected_disposition",
        "escalation_behavior",
    )
    for field in text_fields:
        if not isinstance(case[field], str) or not case[field].strip():
            raise CorpusValidationError(f"{case['id']} has an empty {field}")
    for field in ("required_facts", "acceptable_citations"):
        if not isinstance(case[field], list) or not case[field]:
            raise CorpusValidationError(f"{case['id']} has no {field}")
    if not all(isinstance(fact, str) and fact.strip() for fact in case["required_facts"]):
        raise CorpusValidationError(f"{case['id']} has an invalid required fact")
    if not all(_valid_https_url(url) for url in case["acceptable_citations"]):
        raise CorpusValidationError(f"{case['id']} has an invalid acceptable citation URL")
    if case["source_url"] not in case["acceptable_citations"]:
        raise CorpusValidationError(f"{case['id']} must cite its source issue")


def _load_public_split(corpus_dir: Path, split: str) -> list[dict[str, object]]:
    cases = _read_json(corpus_dir / f"{split}.json")
    if not isinstance(cases, list):
        raise CorpusValidationError(f"{split}.json must contain a list")
    for case in cases:
        _validate_case(case, split)
    return cases


def validate_corpus(corpus_dir: Path) -> CorpusReport:
    """Validate all public splits and the held-out manifest without loading held-out cases."""
    schema = _read_json(corpus_dir / "schema.json")
    if not isinstance(schema, dict) or set(schema.get("required", [])) != REQUIRED_CASE_FIELDS:
        raise CorpusValidationError("schema.json must exactly describe the required case fields")
    lock = _read_json(corpus_dir / "LOCK.json")
    if not isinstance(lock, dict) or lock.get("splits") != {"train": 8, "dev": 4, "heldout": 3}:
        raise CorpusValidationError("LOCK.json must pin the 8/4/3 split")
    split_cases = {split: _load_public_split(corpus_dir, split) for split in OPTIMIZER_SPLITS}
    manifest = _read_json(corpus_dir / "heldout-manifest.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("cases"), list):
        raise CorpusValidationError("heldout-manifest.json must contain a cases list")
    heldout = manifest["cases"]
    if len(heldout) != 3:
        raise CorpusValidationError("held-out manifest must contain exactly three cases")
    for item in heldout:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise CorpusValidationError("held-out manifest contains an invalid entry")
        url = item.get("source_url")
        if not isinstance(url, str) or ISSUE_URL.fullmatch(url) is None:
            raise CorpusValidationError("held-out manifest contains an invalid issue URL")
    ids_by_split = {
        split: {str(case["id"]) for case in cases} for split, cases in split_cases.items()
    }
    ids_by_split["heldout"] = {str(item["id"]) for item in heldout}
    if any(len(ids) != lock["splits"][split] for split, ids in ids_by_split.items()):
        raise CorpusValidationError(
            "a split does not match its locked count or contains duplicate IDs"
        )
    all_ids = [case_id for ids in ids_by_split.values() for case_id in ids]
    if len(set(all_ids)) != len(all_ids):
        raise CorpusValidationError("an issue appears in more than one split")
    return CorpusReport(total_cases=len(all_ids), split_counts=dict(lock["splits"]))


def load_optimizer_cases(corpus_dir: Path, split: str) -> list[dict[str, object]]:
    """Load only optimizer-visible cases; held-out data remains behind the release gate."""
    if split not in OPTIMIZER_SPLITS:
        raise CorpusValidationError(
            "held-out cases are release-gated and cannot be loaded by optimizer code"
        )
    validate_corpus(corpus_dir)
    return _load_public_split(corpus_dir, split)


if __name__ == "__main__":
    report = validate_corpus(Path(__file__).resolve().parents[1] / "corpus")
    print(f"validated {report.total_cases} cases: {report.split_counts}")
