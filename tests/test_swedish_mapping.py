from __future__ import annotations

from wildlife_pipeline.megadetector import SwedishWildlifeDetector


def test_mapping_common_misclassifications():
    d = SwedishWildlifeDetector(model_path=None, conf=0.25)
    m = d._map_to_swedish_wildlife

    assert m("cow") == "moose"
    assert m("horse") == "moose"
    assert m("sheep") == "roedeer"
    assert m("bear") == "boar"
    assert m("dog") == "boar"
    assert m("elephant") == "boar"

    assert m("cat") == "fox"
    assert m("kitten") == "fox"
    assert m("red_fox") == "fox"
    assert m("vulpes_vulpes") == "fox"

    assert m("marten") == "badger"
    assert m("weasel") == "badger"
    assert m("meles_meles") == "badger"


