"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatChartValue, inferChartConfig, readableLabel } from "@/lib/charts/inferChartConfig";
import type { QueryExecutionResponse } from "@/lib/types";

const COLORS = ["#0f766e", "#2563eb", "#9333ea", "#dc2626", "#ca8a04", "#475569"];
const FALLBACK = "This result is best viewed as a table.";

type ChartDatum = Record<string, string | number | null>;

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function chartData(rows: Record<string, unknown>[], valueKey: string): ChartDatum[] {
  return rows
    .map((row) => ({ ...row, [valueKey]: toNumber(row[valueKey]) }))
    .filter((row) => typeof row[valueKey] === "number" && Number.isFinite(row[valueKey] as number)) as ChartDatum[];
}

function tooltipFormatter(value: unknown, name?: string | number) {
  const numeric = toNumber(value);
  const key = String(name ?? "value");
  return [numeric === null ? String(value ?? "") : formatChartValue(key, numeric), readableLabel(key)] as [string, string];
}

function ChartFallback({ message = FALLBACK }: { message?: string }) {
  return (
    <section className="app-surface p-4">
      <h3 className="text-base font-bold text-slate-950">Visualization</h3>
      <p className="mt-3 text-sm text-slate-600">{message}</p>
    </section>
  );
}

export default function ResultChart({ execution, question = "" }: { execution: QueryExecutionResponse; question?: string }) {
  if (!execution.result_rows.length) return <ChartFallback message="No matching results were found. Try changing the question or filters." />;

  const columnOrder = execution.result_columns.map((column) => column.name);
  const { config, reason } = inferChartConfig(execution.result_rows, question, columnOrder);
  if (!config) return <ChartFallback message={reason || FALLBACK} />;

  const valueKey = config.yKey || config.valueKey;
  const nameKey = config.xKey || config.nameKey;
  if (!valueKey || !nameKey) return <ChartFallback />;

  const data = chartData(execution.result_rows, valueKey);
  if (data.length < 2) return <ChartFallback />;

  return (
    <section className="app-surface p-4" aria-label="Visualization of returned query results">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-slate-950">Visualization</h3>
          <p className="mt-1 text-sm text-slate-600">{config.title}</p>
        </div>
        <span className="status-badge border-teal-200 bg-teal-50 text-teal-800">{config.type}</span>
      </div>
      <div className="mt-5 h-80 w-full">
        <ResponsiveContainer height="100%" width="100%">
          {config.type === "line" ? (
            <LineChart data={data} margin={{ bottom: 16, left: 8, right: 16, top: 12 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey={nameKey} tick={{ fontSize: 12 }} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => formatChartValue(valueKey, Number(value))} tickLine={false} width={84} />
              <Tooltip formatter={tooltipFormatter} labelFormatter={(label) => `${readableLabel(nameKey)}: ${label}`} />
              <Line dataKey={valueKey} dot stroke="#0f766e" strokeWidth={3} type="monotone" />
            </LineChart>
          ) : config.type === "pie" ? (
            <PieChart margin={{ bottom: 12, left: 12, right: 12, top: 12 }}>
              <Pie data={data} dataKey={valueKey} nameKey={nameKey} outerRadius={105} label={(entry) => String(entry.name ?? "").slice(0, 18)}>
                {data.map((_entry, index) => <Cell fill={COLORS[index % COLORS.length]} key={index} />)}
              </Pie>
              <Tooltip formatter={tooltipFormatter} />
              <Legend />
            </PieChart>
          ) : (
            <BarChart data={data} margin={{ bottom: 16, left: 8, right: 16, top: 12 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey={nameKey} interval={0} tick={{ fontSize: 12 }} tickLine={false} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => formatChartValue(valueKey, Number(value))} tickLine={false} width={84} />
              <Tooltip formatter={tooltipFormatter} labelFormatter={(label) => `${readableLabel(nameKey)}: ${label}`} />
              <Bar dataKey={valueKey} fill="#0f766e" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{reason}</p>
    </section>
  );
}
