from __future__ import annotations

from typing import Dict, List, Set, Tuple


# ============================================================================
# Regeldefinitionen
# ============================================================================

# EXCLUDES: Zwei Tags dürfen nie gleichzeitig aktiv sein.
EXCLUDES: List[Tuple[str, str, str]] = [
    ("school", "lewd", "Schul Kontext und lewd Inhalte werden hart getrennt."),
    ("studio", "lewd", "Studio Test Szenen sollen nicht mit lewd Content kombiniert werden."),
    ("minimal", "lewd", "Minimal Test Szenen sollen nicht mit lewd Content kombiniert werden."),
    ("wet", "dramatic", "Wet Fabric soll nicht mit dramatischem Licht kombiniert werden, um Artefakte zu vermeiden."),
    ("slice of life", "lewd", "Slice of life Szenen sollen nicht mit lewd Content kombiniert werden."),
]

# REQUIRES: Wenn Trigger Tag aktiv ist, müssen alle Required Tags aktiv sein.
REQUIRES: Dict[str, Tuple[Set[str], str]] = {
    "wind": ({"skirt"}, "Wind Modifier ist nur erlaubt, wenn ein Rock Outfit aktiv ist (Tag skirt)."),
    "rain": ({"rain"}, "Rain Effekte oder Rain Modifier brauchen eine Scene, die ebenfalls Tag rain hat."),
    "adult_only": ({"adult"}, "Adult-only Items sind nur erlaubt, wenn der Charakter Tag adult besitzt."),
    "club": ({"school"}, "Club Aktivitäten gehören in Schul Kontext (Tag school)."),
    "kendo": ({"school", "sport"}, "Kendo ist als School Sport Activity gedacht (Tags school und sport)."),
    "tech": ({"school"}, "Tech Activities gehören in Schul Kontext (Tag school)."),
    "music": ({"school"}, "Music Activities gehören in Schul Kontext (Tag school)."),
    "literature": ({"school"}, "Literature Activities gehören in Schul Kontext (Tag school)."),
    "art": ({"school"}, "Art Activities gehören in Schul Kontext (Tag school)."),
}

# REQUIRES_ANY: Wenn Trigger Tag aktiv ist, muss mindestens eine Gruppe erfüllt sein.
REQUIRES_ANY: Dict[str, Tuple[List[Set[str]], str]] = {
    "swimwear": (
        [{"water"}, {"water_proxy"}],
        "Swimwear ist nur in Wasser Kontext erlaubt (Scene Tag water oder abgeleitetes water_proxy).",
    ),
    "beach": (
        [{"water"}, {"water_proxy"}],
        "Beach Outfits sind nur in Wasser Kontext erlaubt (Scene Tag water oder abgeleitetes water_proxy).",
    ),
    "sport": (
        [{"school"}, {"outdoor"}],
        "Sport Inhalte brauchen entweder Schul Kontext oder Outdoor Kontext (Tag school oder outdoor).",
    ),
    "festival": (
        [{"festival"}, {"festival", "night"}],
        "Festival Inhalte sollen nur im Festival Kontext stattfinden (Tag festival, optional mit night).",
    ),
    "mystery": (
        [{"night"}, {"quiet"}],
        "Mystery Inhalte brauchen meist Night oder Quiet Stimmung (Tag night oder quiet).",
    ),
    "isekai": (
        [{"fantasy"}],
        "Isekai Inhalte brauchen Fantasy Kontext (Tag fantasy).",
    ),
}

# GATES: Vorfilter beim Random Pick.
# kind -> List[(gate_tag, required_active_tags, reason)]
GATES: Dict[str, List[Tuple[str, Set[str], str]]] = {
    "modifier": [
        ("wind", {"skirt"}, "Wind Modifier nur dann picken, wenn ein Rock Outfit aktiv ist."),
        ("rain", {"rain"}, "Rain Modifier nur dann picken, wenn die Scene bereits rain ist."),
        ("club", {"school"}, "Club Modifier nur dann picken, wenn Schul Kontext aktiv ist."),
        ("kendo", {"school", "sport"}, "Kendo Modifier nur dann picken, wenn Schul Sport Kontext aktiv ist."),
    ],
    "outfit": [
        ("adult_only", {"adult"}, "Adult-only Outfits nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Outfits nur dann picken, wenn der Charakter adult ist."),
    ],
    "pose": [
        ("adult_only", {"adult"}, "Adult-only Posen nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Posen nur dann picken, wenn der Charakter adult ist."),
    ],
    "expression": [
        ("adult_only", {"adult"}, "Adult-only Expression nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Expression nur dann picken, wenn der Charakter adult ist."),
    ],
    "lighting": [
        ("dramatic", {"night"}, "Dramatic Lighting bevorzugt nur in night Kontext picken."),
    ],
}
