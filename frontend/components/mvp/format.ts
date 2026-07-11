export function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

export function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "Not available" : value.toLocaleString();
}

export function displayCell(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (["string", "number", "boolean"].includes(typeof value)) return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
