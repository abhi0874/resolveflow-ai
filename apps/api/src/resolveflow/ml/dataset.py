"""Synthetic records only. Group-preserving stratification before fitting any features."""

import hashlib
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import Field

from resolveflow.ml.contracts import LABELS, Category, TicketText

DATASET_VERSION = "ticket-classification-v1"
DATASET_PATH = (
    Path(__file__).resolve().parents[5] / "data/synthetic" / DATASET_VERSION / "tickets.jsonl"
)


class Example(TicketText):
    id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    group_id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    label: Category


def fingerprint(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


def load_dataset(path: Path = DATASET_PATH) -> tuple[list[Example], str]:
    raw = path.read_bytes()
    if len(raw) > 5 * 1024**2:
        raise ValueError("Dataset exceeds limit")
    records = [Example.model_validate_json(line) for line in raw.splitlines() if line.strip()]
    if not 70 <= len(records) <= 5000:
        raise ValueError("Expected 70–5000 synthetic examples")
    seen, ids, groups = set(), set(), {}
    grams = []
    for row in records:
        key = fingerprint(row.combined())
        if key in seen or row.id in ids:
            raise ValueError("Duplicate example or ID; revise the dataset explicitly")
        seen.add(key)
        ids.add(row.id)
        if row.group_id in groups and groups[row.group_id] != row.label:
            raise ValueError("A group must have one label")
        groups[row.group_id] = row.label
        tokens = key.split()
        current = set(zip(tokens, tokens[1:], tokens[2:], strict=False))
        for group, previous in grams:
            union = current | previous
            if group != row.group_id and union and len(current & previous) / len(union) >= 0.8:
                raise ValueError("Near-duplicate examples must share a group")
        grams.append((row.group_id, current))
    if set(groups.values()) != set(LABELS) or min(Counter(groups.values()).values()) < 10:
        raise ValueError("Each category needs at least ten independent scenario groups")
    return records, hashlib.sha256(raw).hexdigest()


def split_dataset(records: list[Example], seed: int) -> dict[str, list[Example]]:
    # Per-label group shuffle: 60/20/20. All paraphrases of one scenario stay together.
    by_label = defaultdict(set)
    for row in records:
        by_label[row.label].add(row.group_id)
    result = {"train": [], "validation": [], "test": []}
    assignment = {}
    for label in LABELS:
        groups = sorted(by_label[label])
        random.Random(f"{seed}:{label}").shuffle(groups)
        n = len(groups)
        if n < 10:
            raise ValueError("Insufficient groups for independent splits")
        train_end, validation_end = int(n * 0.6), int(n * 0.8)
        for i, group in enumerate(groups):
            assignment[group] = (
                "train" if i < train_end else "validation" if i < validation_end else "test"
            )
    for row in sorted(records, key=lambda r: r.id):
        result[assignment[row.group_id]].append(row)
    return result


def split_manifest(splits: dict[str, list[Example]]) -> dict:
    return {
        name: {
            "ids": [r.id for r in rows],
            "groups": sorted({r.group_id for r in rows}),
            "distribution": dict(sorted(Counter(r.label for r in rows).items())),
        }
        for name, rows in splits.items()
    }
