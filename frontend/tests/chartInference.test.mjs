import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const outDir = mkdtempSync(join(tmpdir(), "queryshield-charts-"));
try {
  execFileSync(
    "npx",
    ["tsc", "lib/charts/inferChartConfig.ts", "lib/charts/chartTypes.ts", "--ignoreConfig", "--target", "ES2021", "--lib", "ES2021", "--module", "NodeNext", "--moduleResolution", "NodeNext", "--outDir", outDir, "--skipLibCheck", "--strict"],
    { cwd: new URL("..", import.meta.url), stdio: "inherit", shell: process.platform === "win32" }
  );
  const { inferChartConfig, formatChartValue } = await import(pathToFileURL(join(outDir, "inferChartConfig.js")).href);

  assert.equal(inferChartConfig([
    { region: "East", total_sales: 12500 },
    { region: "West", total_sales: 9800 },
  ]).config?.type, "bar");

  assert.equal(inferChartConfig([
    { month: "Jan", revenue: 12000 },
    { month: "Feb", revenue: 13500 },
  ]).config?.type, "line");

  assert.equal(inferChartConfig([
    { category: "A", percentage: 45 },
    { category: "B", percentage: 30 },
    { category: "C", percentage: 25 },
  ], "Show revenue distribution by category").config?.type, "pie");

  assert.equal(inferChartConfig([{ status: "active" }, { status: "inactive" }]).config, null);
  assert.equal(inferChartConfig([{ total_sales: 12500 }]).config, null);

  const tooMany = Array.from({ length: 21 }, (_, index) => ({ region: `R${index}`, total_sales: index + 1 }));
  assert.equal(inferChartConfig(tooMany).config, null);

  assert.equal(inferChartConfig([
    { region: "East", total_sales: null },
    { region: "West", total_sales: null },
    { region: "South", total_sales: 10 },
  ]).config, null);

  assert.equal(inferChartConfig([
    { customer_id: "C001", total_sales: 10 },
    { customer_id: "C002", total_sales: 20 },
  ]).config, null);

  assert.equal(formatChartValue("percentage", 42), "42%");
  assert.equal(formatChartValue("total_sales", 12500), "$12,500");

  console.log("chart inference tests passed");
} finally {
  rmSync(outDir, { recursive: true, force: true });
}
