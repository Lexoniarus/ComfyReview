from __future__ import annotations

# ============================================================================
# Konfig Flags
# ============================================================================

# Wenn True, dann sind lewd und adult-only Inhalte nur erlaubt,
# wenn der ausgewählte Charakter Tag "adult" besitzt.
ENFORCE_ADULT_TAG: bool = True

# Maximalversuche, falls ihr Reject Looping im Generator nutzt.
# Der Generator kann pro Slot oder pro kompletter Auswahl maximal so oft versuchen.
DEFAULT_MAX_TRIES: int = 200
