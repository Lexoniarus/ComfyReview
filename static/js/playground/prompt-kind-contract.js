export const promptKinds = [
  ["character", "Charakter"],
  ["scene", "Szene"],
  ["atmosphere", "Atmosphäre"],
  ["lighting", "Licht"],
  ["outfit", "Outfit"],
  ["accessory", "Accessoire"],
  ["pose", "Pose"],
  ["expression", "Ausdruck"],
  ["framing", "Bildausschnitt"],
  ["camera_angle", "Kamerawinkel"],
  ["optical_effect", "Optischer Effekt"],
];

export const generatorPromptKinds = promptKinds.map(([kind]) => kind);
