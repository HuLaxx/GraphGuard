#!/usr/bin/env node
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

const args = process.argv.slice(2);
if (args[0] === "--") {
  args.shift();
}

let nextBin;
try {
  nextBin = require.resolve("next/dist/bin/next");
} catch (err) {
  console.error("Failed to resolve Next.js binary:", err);
  process.exit(1);
}

const child = spawn(process.execPath, [nextBin, "dev", "--webpack", ...args], {
  stdio: "inherit",
});

child.on("exit", (code) => {
  process.exit(code ?? 0);
});
