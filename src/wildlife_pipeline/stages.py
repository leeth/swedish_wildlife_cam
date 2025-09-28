from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from pathlib import Path

from .detector import Detection


@dataclass
class StageOneResult:
    """Result of Stage 1 filtering.

    true_positives: Detections believed to be real objects of interest
    false_positives: Detections filtered out as likely spurious
    """
    true_positives: List[Detection]
    false_positives: List[Detection]


class StageOneFalsePositiveFilter:
    """
    Stage 1: Filter obvious false positives using simple heuristics.

    Heuristics:
    - Confidence lower than `min_confidence` → false positive
    - Extremely small boxes relative to image (if width/height given) could be filtered
      (not applied here since we do not have image size context in Detection)
    """

    def __init__(self, min_confidence: float = 0.25):
        self.min_confidence = min_confidence

    def run(self, detections: List[Detection]) -> StageOneResult:
        true_positives: List[Detection] = []
        false_positives: List[Detection] = []
        for det in detections:
            if det.confidence >= self.min_confidence:
                true_positives.append(det)
            else:
                false_positives.append(det)
        return StageOneResult(true_positives=true_positives, false_positives=false_positives)


@dataclass
class StageTwoResult:
    """Result of Stage 2 categorization into human vs animal and species mapping."""
    humans: List[Detection]
    animals: List[Detection]
    species_counts: Dict[str, int]


class StageTwoHumanAnimalAndSpecies:
    """
    Stage 2: Split detections into human vs animal and map to species where possible.

    This uses label-name heuristics so it works with both generic YOLO labels and
    the custom wildlife mappings already done upstream. If a label matches a known
    species name, it is treated as an animal with that species. If it matches a
    human synonym, it is treated as human. Otherwise, it's ignored for species.
    """

    HUMAN_LABELS = {"person", "human", "people"}
    GENERIC_ANIMAL_LABELS = {"animal"}

    # Accepted wildlife species keywords (lowercase) → canonical species name
    SPECIES_MAP = {
        "moose": "moose",
        "elk": "moose",
        "boar": "boar",
        "wild_boar": "boar",
        "wildboar": "boar",
        "roedeer": "roedeer",
        "roe_deer": "roedeer",
        "red_deer": "red_deer",
        "fallow_deer": "fallow_deer",
        "bear": "bear",
        "wolf": "wolf",
        "lynx": "lynx",
        "fox": "fox",
        "badger": "badger",
        "hare": "hare",
        "rabbit": "rabbit",
        # Common misclassifications mapped to nearest target
        "deer": "roedeer",
        "horse": "moose",
        "cow": "moose",
        "sheep": "roedeer",
        "dog": "boar",
        "elephant": "boar",
        "cat": "fox",
        "kitten": "fox",
        "marten": "badger",
        "weasel": "badger",
    }

    def _canonical_species(self, label: str) -> Optional[str]:
        l = label.lower().replace(" ", "_")
        if l in self.SPECIES_MAP:
            return self.SPECIES_MAP[l]
        # partial match fallback
        for key, value in self.SPECIES_MAP.items():
            if key in l:
                return value
        return None

    def run(self, detections: List[Detection]) -> StageTwoResult:
        humans: List[Detection] = []
        animals: List[Detection] = []
        species_counts: Dict[str, int] = {}

        for det in detections:
            label = det.label.lower()
            if label in self.HUMAN_LABELS:
                humans.append(det)
                continue

            species = self._canonical_species(det.label)
            if species is not None or label in self.GENERIC_ANIMAL_LABELS:
                animals.append(det)
                if species is not None:
                    species_counts[species] = species_counts.get(species, 0) + 1

        return StageTwoResult(humans=humans, animals=animals, species_counts=species_counts)


