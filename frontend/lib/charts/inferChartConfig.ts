import type { ChartConfig, ChartInferenceResult } from "./chartTypes";

const CHART_MAX_ROWS = 20;
const BAR_MAX_CATEGORIES = 20;
const PIE_MAX_SLICES = 6;
const LINE_MAX_POINTS = 50;

const NUMERIC_NAME_HINTS = ["sales", "revenue", "amount", "total", "count", "quantity", "average", "avg", "price", "cost", "percentage", "percent", "rate", "share"];
const TEMPORAL_NAME_HINTS = ["date", "created_at", "month", "year", "week", "day", "timestamp", "time", "quarter"];
const COMPOSITION_HINTS = ["share", "percentage", "percent", "distribution", "split", "mix", "portion", "breakdown"];

export function readableLabel(key: string): string {
  return key
    .replaceAll("_", " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

export function formatChartValue(key: string, value: number): string {
  const normalized = key.toLowerCase();
  if (["percentage", "percent", "rate", "share"].some((hint) => normalized.includes(hint))) return `${value.toLocaleString()}%`;
  if (["revenue", "sales", "amount", "price", "cost"].some((hint) => normalized.includes(hint))) return `$${value.toLocaleString()}`;
  return value.toLocaleString();
}

function isPlainChartValue(value: unknown): boolean {
  return value === null || value === undefined || ["string", "number", "boolean"].includes(typeof value);
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function isDateLike(value: unknown): boolean {
  if (value instanceof Date) return !Number.isNaN(value.getTime());
  if (typeof value !== "string" && typeof value !== "number") return false;
  const text = String(value).trim();
  if (!text) return false;
  if (/^\d{4}$/.test(text)) return true;
  if (/^(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)/i.test(text)) return true;
  return !Number.isNaN(Date.parse(text));
}

function isIdentifierColumn(name: string): boolean {
  const normalized = name.toLowerCase();
  return normalized === "id" || normalized.endsWith("_id") || normalized.includes("uuid") || normalized.includes("guid") || normalized.includes("email");
}

function hasHint(name: string, hints: string[]): boolean {
  const normalized = name.toLowerCase();
  return hints.some((hint) => normalized.includes(hint));
}

function nonNullValues(rows: Record<string, unknown>[], key: string): unknown[] {
  return rows.map((row) => row[key]).filter((value) => value !== null && value !== undefined && value !== "");
}

function numericScore(rows: Record<string, unknown>[], key: string): number {
  const values = nonNullValues(rows, key);
  if (values.length < 2 || values.length / rows.length < 0.8) return 0;
  return values.filter((value) => toFiniteNumber(value) !== null).length / values.length;
}

function temporalScore(rows: Record<string, unknown>[], key: string): number {
  const values = nonNullValues(rows, key);
  if (!values.length) return 0;
  return values.filter(isDateLike).length / values.length;
}

function distinctCount(rows: Record<string, unknown>[], key: string): number {
  return new Set(nonNullValues(rows, key).map((value) => String(value))).size;
}

function findNumericKey(rows: Record<string, unknown>[], keys: string[]): string | null {
  return keys
    .filter((key) => numericScore(rows, key) >= 0.8)
    .sort((a, b) => Number(hasHint(b, NUMERIC_NAME_HINTS)) - Number(hasHint(a, NUMERIC_NAME_HINTS)))[0] || null;
}

function findTemporalKey(rows: Record<string, unknown>[], keys: string[], numericKey: string | null): string | null {
  return keys.find((key) => key !== numericKey && (hasHint(key, TEMPORAL_NAME_HINTS) || temporalScore(rows, key) >= 0.8)) || null;
}

function findCategoricalKey(rows: Record<string, unknown>[], keys: string[], numericKey: string | null): string | null {
  return keys.find((key) => {
    if (key === numericKey || isIdentifierColumn(key)) return false;
    const values = nonNullValues(rows, key);
    if (!values.length || values.some((value) => typeof value === "object")) return false;
    const distinct = distinctCount(rows, key);
    return distinct >= 2 && distinct <= BAR_MAX_CATEGORIES;
  }) || null;
}

function titleFor(yKey: string, xKey: string, type: ChartConfig["type"]): string {
  if (type === "pie") return `Distribution by ${readableLabel(xKey)}`;
  return `${readableLabel(yKey)} by ${readableLabel(xKey)}`;
}

export function inferChartConfig(rows: Record<string, unknown>[], question = "", columnOrder?: string[]): ChartInferenceResult {
  if (!rows.length) return { config: null, reason: "No rows returned." };
  if (rows.length < 2) return { config: null, reason: "This result is best viewed as a table." };
  if (rows.some((row) => Object.values(row).some((value) => !isPlainChartValue(value)))) return { config: null, reason: "This result is best viewed as a table." };

  const keys = columnOrder?.length ? columnOrder : Object.keys(rows[0] || {});
  if (keys.length < 2) return { config: null, reason: "This result is best viewed as a table." };

  const numericKey = findNumericKey(rows, keys);
  if (!numericKey) return { config: null, reason: "This result is best viewed as a table." };

  const temporalKey = findTemporalKey(rows, keys, numericKey);
  if (temporalKey && rows.length <= LINE_MAX_POINTS) {
    return {
      config: { type: "line", xKey: temporalKey, yKey: numericKey, title: titleFor(numericKey, temporalKey, "line"), reason: "Temporal and numeric columns detected." },
      reason: "Temporal and numeric columns detected.",
    };
  }

  const categoricalKey = findCategoricalKey(rows, keys, numericKey);
  if (!categoricalKey) return { config: null, reason: "This result is best viewed as a table." };

  const values = rows.map((row) => toFiniteNumber(row[numericKey])).filter((value): value is number => value !== null);
  const compositionHint = hasHint(question, COMPOSITION_HINTS) || hasHint(numericKey, COMPOSITION_HINTS) || hasHint(categoricalKey, COMPOSITION_HINTS);
  if (compositionHint && rows.length <= PIE_MAX_SLICES && values.every((value) => value >= 0)) {
    return {
      config: { type: "pie", nameKey: categoricalKey, valueKey: numericKey, title: titleFor(numericKey, categoricalKey, "pie"), reason: "Composition-style result detected." },
      reason: "Composition-style result detected.",
    };
  }

  if (rows.length > CHART_MAX_ROWS || distinctCount(rows, categoricalKey) > BAR_MAX_CATEGORIES) return { config: null, reason: "This result is best viewed as a table." };

  return {
    config: { type: "bar", xKey: categoricalKey, yKey: numericKey, title: titleFor(numericKey, categoricalKey, "bar"), reason: "Categorical and numeric columns detected." },
    reason: "Categorical and numeric columns detected.",
  };
}

export const chartLimits = { CHART_MAX_ROWS, BAR_MAX_CATEGORIES, PIE_MAX_SLICES, LINE_MAX_POINTS };
