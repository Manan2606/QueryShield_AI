export type ChartType = "bar" | "line" | "pie";

export type ChartConfig = {
  type: ChartType;
  xKey?: string;
  yKey?: string;
  nameKey?: string;
  valueKey?: string;
  title: string;
  description?: string;
  reason: string;
};

export type ChartInferenceResult = {
  config: ChartConfig | null;
  reason: string;
};
