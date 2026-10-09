# Card Battler – erstes tragfähiges Gameplay

**Dokumenttyp:** `WORKING_VISION` · **Priorität:** aktuell zuerst · **Status im Code:** `IN_PROGRESS / POC`, **nicht** fertiges Spiel.

## Fachliche Absicht

Bilder und daraus entwickelte Karten sollen einen **wirklich spielbaren Card Battler** tragen. Bevor die soziale Welt oder die visuelle VN groß ausgebaut werden, soll ein funktionierender Spielkern existieren, an dem Regelmechaniken, Kartenentwicklung und Benutzerabläufe erprobt werden können.

## Was heute schon da ist

Der [aktuelle ComfyReview-POC](../../pocs/card-battler.md) enthält getestete Typen, CardImprint-Mapping, deterministische Stats/Mechaniken/Trait-Entwicklung, Modelladapter und Visual-Prompt-Projektion. **Das ist keine komplette Match-, Deck- oder Karten-Sammlungsoberfläche.** Die konkreten nächsten technischen Arbeitsschritte ergeben sich aus dem POC und seiner Integrationsprüfung.

## Bewusst nicht festgelegt

Ein Fünf-Slot-Feld, 40er-Deck, exakte Turn-Phasen, vollständige Opcode-Registry, Phaser, Match-Persistenzschema und die sieben Phasen des alten [ComfyReview-Card-Battler-Plans](../../archive/card-battler-target-2026-10-02.md) sind **diskutierte oder historische Varianten** – nicht automatisch gültige Anforderungen. Die [ausführlichen Kartenkonzepte](../sources/README.md) können hierfür als Ideenfundus dienen.

**Abhängigkeit:** Der Card Battler soll zuerst funktional erprobt werden. Social-/Academy-/VN-Arbeit darf Ideen oder kleine Spikes vorbereiten, soll den Spielkern aber nicht durch eine verfrühte Gesamtruntime ersetzen.
