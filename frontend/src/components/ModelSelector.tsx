"use client";

import { useEffect, useState } from "react";
import type { ProviderInfo, LLMSelection } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  value: LLMSelection;
  onChange: (selection: LLMSelection) => void;
}

export default function ModelSelector({ value, onChange }: Props) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/providers`)
      .then((res) => res.json())
      .then((data: ProviderInfo[]) => {
        setProviders(data);
        if (data.length > 0 && !value.provider) {
          const defaultProvider = data[0];
          onChange({
            provider: defaultProvider.id,
            model: defaultProvider.default_model,
          });
        }
      })
      .catch(() => {
        setProviders([]);
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentProvider = providers.find((p) => p.id === value.provider);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted">
        <div className="h-3 w-3 animate-spin rounded-full border border-muted border-t-transparent" />
        Loading models...
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={value.provider}
        onChange={(e) => {
          const newProvider = providers.find((p) => p.id === e.target.value);
          if (newProvider) {
            onChange({
              provider: newProvider.id,
              model: newProvider.default_model,
            });
          }
        }}
        className="h-8 rounded-md border border-border bg-surface px-2 text-xs font-medium
                   focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
      >
        {providers.map((p) => (
          <option key={p.id} value={p.id} disabled={!p.configured && p.id !== "local"}>
            {p.label}
            {!p.configured && p.id !== "local" ? " (no API key)" : ""}
          </option>
        ))}
      </select>

      {currentProvider && (
        <select
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          className="h-8 rounded-md border border-border bg-surface px-2 text-xs
                     focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        >
          {currentProvider.models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      )}

      {currentProvider && !currentProvider.configured && value.provider !== "local" && (
        <span className="text-xs text-warning">API key missing</span>
      )}
    </div>
  );
}
