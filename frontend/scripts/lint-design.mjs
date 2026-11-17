#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, "../src");

let errorCount = 0;

// Patterns forbidden in frontend source files per restrained-ui-design-standard
const rules = [
  {
    name: "Oversized radius classes (use rounded-sm, rounded, rounded-md, or rounded-full)",
    regex: /\brounded-(lg|xl|2xl|3xl)\b/g,
  },
  {
    name: "Arbitrary radius brackets (use standard radius tokens)",
    regex: /\brounded-\[/g,
  },
  {
    name: "Heavy font weights (use font-normal, font-medium, or font-semibold)",
    regex: /\bfont-(black|extrabold)\b/g,
  },
  {
    name: "Heavy gradients (use flat surfaces with subtle borders)",
    regex: /\bbg-gradient-[a-z0-9-]+\b/g,
  },
  {
    name: "Backdrop blur (use solid or restrained semi-opaque black)",
    regex: /\bbackdrop-blur-[a-z0-9-]+\b|\bbackdrop-blur\b/g,
  },
  {
    name: "Resting card shadows (shadows reserved for modals/popovers only)",
    regex: /\bshadow-xs\b/g,
  },
  {
    name: "Raw emojis in UI code (use lucide-react icons)",
    regex: /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu,
  },
];

function scanDirectory(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      scanDirectory(fullPath);
    } else if (/\.(tsx|ts|jsx|js|html)$/.test(entry.name)) {
      checkFile(fullPath);
    }
  }
}

function checkFile(filePath) {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const relPath = path.relative(path.resolve(__dirname, ".."), filePath);

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")) {
      return;
    }

    for (const rule of rules) {
      if (rule.regex.test(line)) {
        console.error(`\x1b[31m[DESIGN VIOLATION]\x1b[0m ${relPath}:${idx + 1} - ${rule.name}`);
        console.error(`  > ${trimmed}`);
        errorCount++;
      }
      rule.regex.lastIndex = 0;
    }
  });
}

console.log(`Scanning frontend source directory: ${srcDir}...`);
scanDirectory(srcDir);

if (errorCount > 0) {
  console.error(`\n\x1b[31mFailed: ${errorCount} design standard violation(s) found.\x1b[0m`);
  process.exit(1);
} else {
  console.log(`\n\x1b[32mPassed: All frontend source files comply with the design system standard.\x1b[0m`);
  process.exit(0);
}
