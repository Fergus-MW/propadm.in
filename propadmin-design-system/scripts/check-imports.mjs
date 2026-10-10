import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const declared = new Set(Object.keys({ ...manifest.dependencies, ...manifest.devDependencies }));
let count = 0;
let errors = 0;
function visitFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const ast = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true);
  function visit(node) {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
      const spec = node.moduleSpecifier.text;
      count++;
      if (spec.startsWith(".") || spec.startsWith("@/")) {
        const base = spec.startsWith("@/") ? path.join(root, spec.slice(2)) : path.resolve(path.dirname(file), spec);
        if (![base, base + ".ts", base + ".tsx", path.join(base, "index.ts"), path.join(base, "index.tsx")].some(p => fs.existsSync(p))) {
          console.error(`Missing import: ${path.relative(root, file)} -> ${spec}`);
          errors++;
        }
      } else {
        const packageName = spec.startsWith("@") ? spec.split("/").slice(0, 2).join("/") : spec.split("/")[0];
        if (!spec.startsWith("node:") && !declared.has(packageName)) {
          console.error(`Undeclared dependency: ${spec}`);
          errors++;
        }
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(ast);
}
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (/\.tsx?$/.test(entry.name)) visitFile(file);
  }
}
for (const dir of ["components", "hooks", "lib"]) walk(path.join(root, dir));
console.log(`Checked ${count} source imports/exports; ${errors} errors.`);
process.exitCode = errors ? 1 : 0;
