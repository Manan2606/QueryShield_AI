import type { ApiPanelState } from "@/lib/types";

function maskToken(token: string): string {
  if (token.length <= 14) {
    return "[masked]";
  }
  return `${token.slice(0, 7)}...${token.slice(-6)}`;
}

function maskSensitiveData(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(maskSensitiveData);
  }

  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return Object.fromEntries(
      Object.entries(record).map(([key, item]) => {
        if (key === "access_token" && typeof item === "string") {
          return [key, maskToken(item)];
        }
        if (key.toLowerCase().includes("password")) {
          return [key, "[removed]"];
        }
        return [key, maskSensitiveData(item)];
      }),
    );
  }

  return value;
}

type ApiResponsePanelProps = {
  response: ApiPanelState | null;
};

export default function ApiResponsePanel({ response }: ApiResponsePanelProps) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 text-slate-100 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold">API Response / Error Viewer</h2>
          <p className="text-sm text-slate-400">Latest backend operation output.</p>
        </div>
        {response ? (
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${response.ok ? "bg-emerald-400 text-emerald-950" : "bg-rose-400 text-rose-950"}`}>
            {response.ok ? "Success" : "Error"}
          </span>
        ) : null}
      </div>
      {response ? (
        <div className="space-y-3">
          <div className="grid gap-2 text-sm text-slate-300 sm:grid-cols-3">
            <div><span className="text-slate-500">Operation:</span> {response.operation}</div>
            <div><span className="text-slate-500">Status:</span> {response.status ?? (response.ok ? "OK" : "Failed")}</div>
            <div><span className="text-slate-500">Time:</span> {response.timestamp}</div>
          </div>
          <pre className="max-h-96 overflow-auto rounded-md bg-slate-900 p-3 text-xs leading-relaxed text-slate-100">
            {JSON.stringify(maskSensitiveData(response.ok ? response.data : response.error), null, 2)}
          </pre>
        </div>
      ) : (
        <div className="rounded-md bg-slate-900 p-3 text-sm text-slate-400">No API calls yet.</div>
      )}
    </div>
  );
}
