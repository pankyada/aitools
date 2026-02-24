"""Entity and relationship extraction helpers."""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedEntity:
    """Extracted entity result."""

    name: str
    canonical_name: str
    entity_type: str


@dataclass(slots=True)
class ExtractedRelationship:
    """Extracted relationship result."""

    entity_a: str
    entity_b: str
    relation_type: str
    context: str


def extract_entities(text: str) -> list[ExtractedEntity]:
    """Extract entities from text using spaCy when available.

    Args:
        text: Source text.

    Returns:
        Extracted entities.

    Raises:
        None.
    """

    try:
        import spacy

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        out: list[ExtractedEntity] = []
        for ent in doc.ents:
            normalized = ent.text.strip()
            if not normalized:
                continue
            out.append(
                ExtractedEntity(
                    name=normalized,
                    canonical_name=normalized.lower(),
                    entity_type=_map_label(ent.label_),
                )
            )
        return _dedupe_entities(out)
    except Exception:
        pattern = re.compile(r"\b[A-Z][a-zA-Z0-9_-]{2,}\b")
        candidates = pattern.findall(text)
        entities = [
            ExtractedEntity(name=item, canonical_name=item.lower(), entity_type="CONCEPT")
            for item in candidates
        ]
        return _dedupe_entities(entities)


def _map_label(label: str) -> str:
    """Map spaCy label names to tool schema labels.

    Args:
        label: spaCy entity label.

    Returns:
        Normalized entity type.

    Raises:
        None.
    """

    mapping = {
        "PERSON": "PERSON",
        "ORG": "ORG",
        "GPE": "LOCATION",
        "LOC": "LOCATION",
        "DATE": "DATE",
        "TIME": "DATE",
    }
    return mapping.get(label, "CONCEPT")


def _dedupe_entities(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """Deduplicate entities by canonical name.

    Args:
        entities: Candidate entities.

    Returns:
        Deduplicated entities.

    Raises:
        None.
    """

    seen: set[str] = set()
    unique: list[ExtractedEntity] = []
    for entity in entities:
        if entity.canonical_name in seen:
            continue
        seen.add(entity.canonical_name)
        unique.append(entity)
    return unique


def extract_relationships(
    text: str, entities: list[ExtractedEntity]
) -> list[ExtractedRelationship]:
    """Extract simple co-occurrence relationships.

    Args:
        text: Source text.
        entities: Extracted entities.

    Returns:
        Co-occurrence relationships.

    Raises:
        None.
    """

    _ = text
    relationships: list[ExtractedRelationship] = []
    names = [entity.canonical_name for entity in entities]
    for a, b in itertools.combinations(names, 2):
        relationships.append(
            ExtractedRelationship(
                entity_a=a,
                entity_b=b,
                relation_type="RELATED_TO",
                context="Co-mentioned in memory entry",
            )
        )
    return relationships
