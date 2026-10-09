# Visuelle Novel – bewusster letzter Ausbauschritt

**Dokumentklasse:** `WORKING_VISION` · **Priorität:** letzter großer visueller Produktausbau · **Status im aktuellen ComfyReview:** nicht als VN-Gesamtsystem integriert.

## Fachliche Absicht

Eine visuelle Novel (VN) kann die bisher aufgebauten Figuren, die soziale Welt und den Academy-/Schuljahresverlauf später **szenisch** erlebbar machen. Sie ist die aufwendige Darstellungsschicht über zuvor entwickelten Spiel- und Interaktionsmechaniken, **nicht der technische Startpunkt**.

## Warum diese Arbeit bewusst später kommt

- **Figurenfreistellung** aus generierten Bildern benötigt verlässliche Segmentierung, Maskierung beziehungsweise Matting.
- Eine Szene besteht aus mehreren **visuellen Ebenen** und muss Figuren, Hintergründe, Positionen, Ausdruck, Beleuchtung und Stil konsistent zusammensetzen.
- Produktions-/Qualitäts-/Recoveryfragen von Bildassets können erheblich komplexer werden als eine zunächst text- und datenbasierte Timeline oder Chat-Oberfläche.

**Diese Risiken dürfen früh durch kleine Feasibility-POCs untersucht werden.** Das ist etwas anderes, als jetzt schon eine komplette VN-Pipeline oder szenische UI zu implementieren.

## Nicht festgeschrieben

Weder Phaser noch ein bestimmtes Canvas-/DOM-Verfahren, Sprite-Pipeline, Art-Asset-Schema, LLM-Vertrag, UI-Navigation oder alte M4-/M6-/Schema-v58-Architektur sind durch das Zielbild beschlossen. Die [historischen Quellen](../sources/README.md) sind als mögliche Ideen zu lesen. Die priorisierte Entwicklung bleibt [Card Battler → Social → Academy → visuelle VN](README.md), mit möglichen Überschneidungen vor dem VN-Ausbau.
