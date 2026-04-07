import { useEffect, useMemo, useState } from "react";
import { NeoButton, NeoPanel } from "jeikei-design-system";
import { RefreshCw } from "lucide-react";

const SECRET_FIELDS = [
  { key: "BYBIT_API_KEY", label: "BYBIT_API_KEY" },
  { key: "BYBIT_API_SECRET", label: "BYBIT_API_SECRET" },
  { key: "BYBIT_MASTER_UID", label: "BYBIT_MASTER_UID" },
  { key: "EXCHANGE_NAME", label: "EXCHANGE_NAME", type: "select", options: ["binance", "bybit", "okx", "binanceus", "coinbase", "kraken", "okx"] },
  { key: "OLLAMA_URL", label: "OLLAMA_URL" },
  { key: "OPENAI_API_KEY", label: "OPENAI_API_KEY" },
  { key: "GEMINI_API_KEY", label: "GEMINI_API_KEY" },
  { key: "VOYAGE_API_KEY", label: "VOYAGE_API_KEY" },
  { key: "MISTRAL_API_KEY", label: "MISTRAL_API_KEY" },
  { key: "GITHUB_TOKEN", label: "GITHUB_TOKEN" },
  { key: "ORACLE_API_KEY", label: "ORACLE_API_KEY" },
  { key: "JEIKEI_TOKEN", label: "JEIKEI_TOKEN" },
  { key: "TELEGRAM_BOT_TOKEN", label: "TELEGRAM_BOT_TOKEN" },
  { key: "GOPLACES_API_KEY", label: "GOPLACES_API_KEY" },
  { key: "NANO_BANANA_API_KEY", label: "NANO_BANANA_API_KEY" },
  { key: "NOTION_API_KEY", label: "NOTION_API_KEY" },
  { key: "CCXT_PROXY_URL", label: "CCXT_PROXY_URL" },
];

export default function Settings() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadSecrets = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/v1/secrets`);
      const json = await res.json();
      setSecrets(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSecrets();
  }, []);

  const handleChange = (key: string, value: string) => {
    setSecrets((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`${apiBase}/v1/secrets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          Object.fromEntries(
            Object.entries(secrets).map(([k, v]) => [k, v || undefined])
          )
        ),
      });
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 text-white space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-blue-400">Credenciales y API Keys</h1>
          <p className="text-slate-400 text-sm">Edita los secretos usados por Supervisor, UAEs y OpenClaw.</p>
        </div>
        <NeoButton onClick={loadSecrets} variant="secondary">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refrescar
        </NeoButton>
      </header>

      <NeoPanel glow className="border-white/10 p-4">
        <div className="grid md:grid-cols-2 gap-3">
          {SECRET_FIELDS.map((field) =>
            field.type === "select" ? (
              <div key={field.key} className="flex flex-col gap-1">
                <label className="text-xs text-slate-400">{field.label}</label>
                <select
                  className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm text-white"
                  value={secrets[field.key] || field.options?.[0] || ""}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                >
                  {field.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <input
                key={field.key}
                className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm"
                placeholder={field.label}
                value={secrets[field.key] || ""}
                onChange={(e) => handleChange(field.key, e.target.value)}
              />
            )
          )}
        </div>
        <div className="flex justify-end mt-4">
          <NeoButton onClick={handleSave} disabled={saving}>
            {saving ? "Guardando..." : "Guardar"}
          </NeoButton>
        </div>
      </NeoPanel>
    </div>
  );
}
