# Visuelle Novel – bewusster letzter Ausbauschritt

**Dokumentklasse:** `WORKING_VISION` · **Priorität:** letzter großer visueller Produktausbau · **Status im aktuellen ComfyReview:** nicht als VN-Gesamtsystem integriert.

## Fachliche Absicht

**Die eigentliche VN-Content-Entwicklung kommt zuletzt.** Die Visual Novel soll die dann vorhandenen Figuren, Timeline-/Social-Interaktionen und die [Storyline](storyline.md) später **szenisch** erlebbar machen. Ein möglicher [Academy-/Schuljahresrahmen](academy-and-world.md) kann zu dieser Geschichte gehören, ist aber keine vorgeschriebene zusätzliche Entwicklungsphase. Die VN ist **nicht** der technische Startpunkt; kleinere vorbereitende Machbarkeits-POCs sind davon zu unterscheiden.

## Warum diese Arbeit bewusst später kommt

- **Figurenfreistellung** aus generierten Bildern benötigt verlässliche Segmentierung, Maskierung beziehungsweise Matting.
- Eine Szene besteht aus mehreren **visuellen Ebenen** und muss Figuren, Hintergründe, Positionen, Ausdruck, Beleuchtung und Stil konsistent zusammensetzen.
- Produktions-/Qualitäts-/Recoveryfragen von Bildassets können erheblich komplexer werden als eine zunächst text- und datenbasierte Timeline oder Chat-Oberfläche.

**Diese Risiken dürfen früh durch kleine Feasibility-POCs untersucht werden.** Das ist etwas anderes, als jetzt schon eine komplette VN-Pipeline oder szenische UI zu implementieren.

## Nicht festgeschrieben

Weder Phaser noch ein bestimmtes Canvas-/DOM-Verfahren, Sprite-Pipeline, Art-Asset-Schema, LLM-Vertrag, UI-Navigation oder alte M4-/M6-/Schema-v58-Architektur sind durch das Zielbild beschlossen. Die [historischen Quellen](../sources/README.md) sind als mögliche Ideen zu lesen. Die grobe Richtung bleibt [Card Battler → Timeline → Social/Chat → Storyline → VN-Content zuletzt](README.md). Technische Feasibility-POCs vorher sind möglich, **die eigentliche VN-Inhaltsproduktion nicht vorgezogen**.
