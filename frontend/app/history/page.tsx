"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/mvp/AppShell";
import QueryHistorySection from "@/components/QueryHistorySection";
import ErrorAlert from "@/components/mvp/ErrorAlert";
import * as api from "@/lib/api";
import type { Dataset } from "@/lib/types";

export default function HistoryPage() {
  return <AppShell title="Query History">{({ token }) => <HistoryContent token={token} />}</AppShell>;
}

function HistoryContent({ token }: { token: string }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.listDatasets(token)
      .then((data) => { if (mounted) setDatasets(data); })
      .catch((err) => { if (mounted) setError(err instanceof api.ApiError ? err.message : "Datasets failed to load."); });
    return () => { mounted = false; };
  }, [token]);

  return (
    <div className="space-y-4">
      <ErrorAlert message={error} />
      <QueryHistorySection token={token} datasets={datasets} onResult={() => undefined} onError={(_operation, err) => setError(err instanceof api.ApiError ? err.message : "Query history request failed.")} />
    </div>
  );
}