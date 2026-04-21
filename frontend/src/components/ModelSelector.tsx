"use client";

import { useEffect, useState } from "react";
import type { ProviderInfo, LLMSelection } from "@/types";
import { API_BASE } from "@/lib/config";

interface Props {
  value: LLMSelection;
  onChange: (selection: LLMSelection) => void;
}

export default function ModelSelector({ value, onChange }: Props) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/providers`)
      .then((res) => res.json())
      .then((data: ProviderInfo[]) => {
        setProviders(data);
        setFetchError(false);
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
        setFetchError(true);
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

  if (fetchError) {
    return (
      <div className="flex items-center gap-2 text-xs text-danger">
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
        Backend unreachable
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
