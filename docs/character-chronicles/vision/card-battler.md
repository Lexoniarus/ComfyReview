# Card Battler – erstes tragfähiges Gameplay

**Dokumentklasse:** `WORKING_VISION` · **Priorität:** aktuell zuerst · **Status im Code:** `IN_PROGRESS / POC`, **nicht** fertiges Spiel.

## Fachliche Absicht

Bilder und daraus entwickelte Karten sollen einen **wirklich spielbaren Card Battler** tragen. Bevor Timeline, die breitere Social-/Chat-Plattform, Storyline oder VN-Content groß ausgebaut werden, soll ein funktionierender Spielkern existieren, an dem Regelmechaniken, Kartenentwicklung und Benutzerabläufe erprobt werden können.

## Was heute schon da ist

Der [aktuelle ComfyReview-POC](../../pocs/card-battler.md) enthält getestete Typen, CardImprint-Mapping, deterministische Stats/Mechaniken/Trait-Entwicklung, Modelladapter und Visual-Prompt-Projektion. **Das ist keine komplette Match-, Deck- oder Karten-Sammlungsoberfläche.** Die konkreten nächsten technischen Arbeitsschritte ergeben sich aus dem POC und seiner Integrationsprüfung.

## Späteres Spielerziel in Character Chronicles

Im späteren Spiel soll die Kartenerzeugung **vier zum Karteninhalt
passende Bildvarianten** anbieten, aus denen der Spieler **eine
auswählt** und als Karte übernimmt. Die Auswahl ist Teil des
angestrebten Spielerlebnisses, **nicht** bereits implementiert und
noch kein Vertrag über Renderer, Kartenspeicherung oder Kampfregeln.

## Aktueller ComfyReview-Entwicklungs-POC

Der [aktive Versuch in ComfyReview](../../pocs/card-battler.md#konkreter-erstversuch-eine-karte-von-der-bildwahl-bis-zur-sammlung)
beginnt jeweils mit **einem vorhandenen Bild**, aus dem zusammenpassende
Kartenwerte, Kartentext und vier neue Bildalternativen hervorgehen
sollen. **Während der Entwicklung** darf der Nutzer eine Alternative
auswählen **oder alle vier ablehnen und erneut generieren**. Auch bei
einer Weiterentwicklung bleibt die zuletzt bestätigte Karte bei
Ablehnung unverändert. Dieses zusätzliche Ablehnungs-/Retry-Verhalten
dient der Erprobung in ComfyReview und ist **keine automatisch gültige
Spielregel für Character Chronicles**.

Für den POC sollen so schrittweise **40 einzeln bestätigte Karten**
als erstes Testdeck entstehen. Eine kleine Oberfläche für
Erzeugung, Vergleich, Sammlung und Entwicklung gehört zum Versuch.
**Der POC ist weder eine bereits fertige End-to-End-Funktion noch
eine endgültige Spielregel.** Die Zahl 40 ist insbesondere keine
allgemeine spätere Deckgrößenvorgabe.

## Bewusst nicht festgelegt

Ein Fünf-Slot-Feld, eine **dauerhaft verbindliche 40-Karten-Deckregel**,
exakte Turn-Phasen, vollständige Opcode-Registry, Phaser,
Match-Persistenzschema und die sieben Phasen des alten
[ComfyReview-Card-Battler-Plans](../../archive/card-battler-target-2026-10-02.md)
sind **diskutierte oder historische Varianten** – nicht automatisch gültige
Anforderungen. Die [ausführlichen Kartenkonzepte](../sources/README.md)
können hierfür als Ideenfundus dienen.

**Abhängigkeit:** Der Card Battler soll zuerst funktional erprobt werden. Spätere Schwerpunkte sind **Timeline → Social Network mit Chats → Storyline → VN-Content zuletzt**. Academy/Schuljahr ist möglicher Weltkontext der Storyline, kein zusätzlich beschlossenes Release-Gate. Kleine übergreifende POCs sind zulässig, dürfen aber den Spielkern nicht durch eine vorgezogene Gesamtruntime ersetzen.
