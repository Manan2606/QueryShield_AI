import type { QueryExecutionResponse } from "@/lib/types";

type ChartPoint = {
  label: string;
  value: number;
};

type ChartModel = {
  type: "bar" | "line";
  title: string;
  xLabel: string;
  yLabel: string;
  points: ChartPoint[];
};

function isNumeric(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function looksNumeric(value: unknown): boolean {
  if (isNumeric(value)) return true;
  if (typeof value !== "string" || !value.trim()) return false;
  return Number.isFinite(Number(value));
}

function toNumber(value: unknown): number | null {
  if (isNumeric(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function isIdentifierColumn(name: string): boolean {
  const normalized = name.toLowerCase();
  return normalized === "id" || normalized.endsWith("_id") || normalized.includes("uuid") || normalized.includes("guid");
}

function isTimeColumn(name: string): boolean {
  const normalized = name.toLowerCase();
  return ["date", "time", "month", "year", "quarter", "week", "day"].some((part) => normalized.includes(part));
}

function buildChart(execution: QueryExecutionResponse): ChartModel | null {
  const rows = execution.result_rows;
  if (rows.length < 2 || rows.length > 30) return null;
  const headers = execution.result_columns.length ? execution.result_columns.map((column) => column.name) : Object.keys(rows[0] || {});
  if (headers.length < 2) return null;

  const numericHeader = headers.find((header) => rows.some((row) => looksNumeric(row[header])) && rows.every((row) => row[header] === null || row[header] === undefined || looksNumeric(row[header])));
  const dimensionHeader = headers.find((header) => header !== numericHeader && !isIdentifierColumn(header) && rows.some((row) => row[header] !== null && row[header] !== undefined));
  if (!numericHeader || !dimensionHeader) return null;

  const points = rows
    .map((row) => ({ label: String(row[dimensionHeader] ?? "Unknown"), value: toNumber(row[numericHeader]) }))
    .filter((point): point is ChartPoint => point.value !== null && point.label.trim().length > 0);

  if (points.length < 2) return null;
  const type = isTimeColumn(dimensionHeader) ? "line" : "bar";
  return {
    type,
    title: `${numericHeader.replaceAll("_", " ")} by ${dimensionHeader.replaceAll("_", " ")}`,
    xLabel: dimensionHeader.replaceAll("_", " "),
    yLabel: numericHeader.replaceAll("_", " "),
    points,
  };
}

function BarChart({ points }: { points: ChartPoint[] }) {
  const max = Math.max(...points.map((point) => Math.abs(point.value)), 1);
  return (
    <div className="space-y-3" role="img" aria-label="Bar chart of compatible result data">
      {points.map((point) => {
        const width = Math.max(3, Math.round((Math.abs(point.value) / max) * 100));
        return (
          <div className="grid gap-2 sm:grid-cols-[minmax(8rem,14rem)_1fr]" key={point.label}>
            <div className="truncate text-sm font-semibold text-slate-700" title={point.label}>{point.label}</div>
            <div className="flex items-center gap-2">
              <div className="h-7 flex-1 rounded-md bg-slate-100">
                <div className="h-7 rounded-md bg-teal-600" style={{ width: `${width}%` }} />
              </div>
              <span className="w-24 text-right text-sm font-semibold text-slate-900">{point.value.toLocaleString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LineChart({ points }: { points: ChartPoint[] }) {
  const width = 640;
  const height = 220;
  const padding = 28;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coordinates = points.map((point, index) => {
    const x = padding + (index / Math.max(points.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((point.value - min) / range) * (height - padding * 2);
    return { x, y, point };
  });
  const path = coordinates.map((coordinate, index) => `${index === 0 ? "M" : "L"} ${coordinate.x} ${coordinate.y}`).join(" ");

  return (
    <div className="overflow-x-auto" role="img" aria-label="Line chart of compatible time-based result data">
      <svg className="min-w-[34rem]" viewBox={`0 0 ${width} ${height}`}>
        <line stroke="#cbd5e1" x1={padding} x2={padding} y1={padding} y2={height - padding} />
        <line stroke="#cbd5e1" x1={padding} x2={width - padding} y1={height - padding} y2={height - padding} />
        <path d={path} fill="none" stroke="#0f766e" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
        {coordinates.map(({ x, y, point }) => (
          <g key={`${point.label}-${x}`}>
            <circle cx={x} cy={y} fill="#0f766e" r="4" />
            <title>{`${point.label}: ${point.value.toLocaleString()}`}</title>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function ResultChart({ execution }: { execution: QueryExecutionResponse }) {
  const chart = buildChart(execution);

  if (!execution.result_rows.length) {
    return (
      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">Chart</h3>
        <p className="mt-3 text-sm text-slate-600">No matching results were found. Try changing the question or filters.</p>
      </section>
    );
  }

  if (!chart) {
    return (
      <section className="app-surface p-4">
        <h3 className="text-base font-bold text-slate-950">Chart</h3>
        <p className="mt-3 text-sm text-slate-600">This result is best viewed as a table.</p>
      </section>
    );
  }

  return (
    <section className="app-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold capitalize text-slate-950">{chart.type} chart</h3>
          <p className="mt-1 text-sm text-slate-600">{chart.title}</p>
        </div>
        <span className="status-badge border-teal-200 bg-teal-50 text-teal-800">Compatible</span>
      </div>
      <div className="mt-5">
        {chart.type === "line" ? <LineChart points={chart.points} /> : <BarChart points={chart.points} />}
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        <span>X-axis: {chart.xLabel}</span>
        <span>Y-axis: {chart.yLabel}</span>
      </div>
    </section>
  );
}