import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);

function filesBelow(directory, suffix) {
  if (!fs.existsSync(directory)) {
    return [];
  }
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory()
      ? filesBelow(target, suffix)
      : entry.name.endsWith(suffix)
        ? [target]
        : [];
  });
}

function relative(file) {
  return path.relative(root, file).replaceAll("\\", "/");
}

function listedFiles(listPath) {
  return fs
    .readFileSync(path.join(root, listPath), "utf8")
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

describe("frontend architecture", () => {
  it("keeps fetch ownership inside ApiClient", () => {
    const violations = filesBelow(path.join(root, "static/js"), ".js")
      .filter((file) => relative(file) !== "static/js/core/api-client.js")
      .filter((file) => /\bfetch\s*\(/u.test(fs.readFileSync(file, "utf8")))
      .map(relative);

    expect(violations).toEqual([]);
  });

  it("does not construct dynamic HTML strings", () => {
    const violations = filesBelow(path.join(root, "static/js"), ".js")
      .filter((file) => /\.innerHTML\s*=/u.test(fs.readFileSync(file, "utf8")))
      .map(relative);

    expect(violations).toEqual([]);
  });

  it("keeps migrated templates free of inline code and style", () => {
    const violations = [];
    for (const template of listedFiles(
      "quality/frontend_migrated_templates.txt",
    )) {
      const source = fs.readFileSync(path.join(root, template), "utf8");
      if (/<script(?![^>]*\bsrc=)[^>]*>/iu.test(source)) {
        violations.push(`${template}:inline-script`);
      }
      if (/<style\b/iu.test(source) || /\sstyle\s*=/iu.test(source)) {
        violations.push(`${template}:inline-style`);
      }
    }

    expect(violations).toEqual([]);
  });

  it("keeps view components independent from ApiClient", () => {
    const viewRoots = ["components", "images", "inspector", "scopes"];
    const violations = viewRoots
      .flatMap((directory) =>
        filesBelow(path.join(root, "static/js", directory), ".js"),
      )
      .filter((file) => /api-client\.js/u.test(fs.readFileSync(file, "utf8")))
      .map(relative);

    expect(violations).toEqual([]);
  });
});
