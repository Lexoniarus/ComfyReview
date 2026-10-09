# Card Battler – erstes tragfähiges Gameplay

**Dokumentklasse:** `WORKING_VISION` · **Priorität:** aktuell zuerst · **Status im Code:** `IN_PROGRESS / POC`, **nicht** fertiges Spiel.

## Fachliche Absicht

Bilder und daraus entwickelte Karten sollen einen **wirklich spielbaren Card Battler** tragen. Bevor die soziale Welt oder die visuelle VN groß ausgebaut werden, soll ein funktionierender Spielkern existieren, an dem Regelmechaniken, Kartenentwicklung und Benutzerabläufe erprobt werden können.

## Was heute schon da ist

Der [aktuelle ComfyReview-POC](../../pocs/card-battler.md) enthält getestete Typen, CardImprint-Mapping, deterministische Stats/Mechaniken/Trait-Entwicklung, Modelladapter und Visual-Prompt-Projektion. **Das ist keine komplette Match-, Deck- oder Karten-Sammlungsoberfläche.** Die konkreten nächsten technischen Arbeitsschritte ergeben sich aus dem POC und seiner Integrationsprüfung.

## Aktuelles, begrenztes POC-Ziel

Der [aktive Versuch in ComfyReview](../../pocs/card-battler.md#konkreter-erstversuch-eine-karte-von-der-bildwahl-bis-zur-sammlung)
soll **jeweils ein vorhandenes Bild** als Ausgangspunkt nehmen, daraus
**zusammenpassende Kartenwerte und Kartentext** entwerfen, **vier passende
Bildvarianten** anbieten und den Spieler **eine** davon für die Karte
auswählen lassen. Eine bestehende Karte soll danach mit demselben
Auswahlprinzip weiterentwickelt werden können. Für ein erstes Testdeck
sollen so **40 einzelne Karten** entstehen. Eine kleine Oberfläche
für Erzeugung, Auswahl, Sammlung und Entwicklung gehört zum Versuch.

**Das ist ein gegenwärtiges Experimentziel, weder bereits implementierte
End-to-End-Funktion noch endgültige Spielregel.** Insbesondere sind die
40 Karten nicht als generelle Pflichtgröße jedes künftigen Decks festgelegt.

## Bewusst nicht festgelegt

Ein Fünf-Slot-Feld, eine **dauerhaft verbindliche 40-Karten-Deckregel**,
exakte Turn-Phasen, vollständige Opcode-Registry, Phaser,
Match-Persistenzschema und die sieben Phasen des alten
[ComfyReview-Card-Battler-Plans](../../archive/card-battler-target-2026-10-02.md)
sind **diskutierte oder historische Varianten** – nicht automatisch gültige
Anforderungen. Die [ausführlichen Kartenkonzepte](../sources/README.md)
können hierfür als Ideenfundus dienen.

**Abhängigkeit:** Der Card Battler soll zuerst funktional erprobt werden. Social-/Academy-/VN-Arbeit darf Ideen oder kleine Spikes vorbereiten, soll den Spielkern aber nicht durch eine verfrühte Gesamtruntime ersetzen.
