import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import postcss from "postcss";
import tailwind from "@tailwindcss/postcss";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const input = path.join(root, "styles/globals.css");
const css = (await fs.readFile(input, "utf8"))
  .replace('@import "tailwindcss";', '@import "tailwindcss" source(none);')
  + '\n@source "../components";\n@source "../hooks";\n@source "../lib";\n@source "../preview";\n';
const result = await postcss([tailwind({ optimize: true })]).process(css, {
  from: input,
  to: path.join(root, "styles/design-system.css"),
});
await fs.writeFile(path.join(root, "styles/design-system.css"), result.css);
console.log("Built styles/design-system.css");
