import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Coins, Cpu, RefreshCw } from "lucide-react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useMemo } from "react";

type ContainerInfo = { name: string; status: string; id: string };
type SectorInfo = { sector_name: string; discoverer_uae_id: string; status: string; created_at: string };
type StatusPayload = { containers: ContainerInfo[]; sectors: SectorInfo[]; genesis_balance: Record<string, number> };

export default function Home() {
  const [data, setData] = useState<StatusPayload>({ containers: [], sectors: [], genesis_balance: {} });
  const [loading, setLoading] = useState(false);
  const [showContainers, setShowContainers] = useState(false);
   const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [bybitKey, setBybitKey] = useState("");
  const [bybitSecret, setBybitSecret] = useState("");
  const [bybitUid, setBybitUid] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("");

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/v1/status`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
    const id = setInterval(loadStatus, 5000);
    return () => clearInterval(id);
  }, []);

  const totalUSDT = data.genesis_balance["USDT"] || 0;
  const totalUSDC = data.genesis_balance["USDC"] || 0;

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <header className="flex justify-between items-center mb-8 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tighter text-blue-400">AUTOMATA SUPERVISOR</h1>
          <p className="text-slate-400 text-sm">UAEs, Bybit, Ollama remoto</p>
        </div>
        <button
          onClick={loadStatus}
          className="flex items-center gap-2 text-sm px-3 py-2 rounded border border-white/10 hover:border-blue-400"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="bg-black/40 border-white/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">UAEs Activos</CardTitle>
            <Activity className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="text-3xl font-bold">{data.containers.length}</div>
              <button
                onClick={() => setShowContainers((v) => !v)}
                className="text-sm flex items-center gap-1 text-blue-300"
              >
                {showContainers ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                Detalle
              </button>
            </div>
            {showContainers && (
              <ul className="mt-3 space-y-1 text-sm text-slate-300">
                {data.containers.map((c) => (
                  <li key={c.id} className="flex justify-between">
                    <span>{c.name}</span>
                    <span className="text-emerald-400 uppercase text-xs">{c.status}</span>
                  </li>
                ))}
                {data.containers.length === 0 && <li className="text-slate-500">Sin UAEs (monitor lanzará UAE-Alpha)</li>}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-white/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Saldo Génesis (Bybit)</CardTitle>
            <Coins className="h-4 w-4 text-yellow-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">USDT: {totalUSDT.toFixed(2)}</div>
            <div className="text-xl font-semibold">USDC: {totalUSDC.toFixed(2)}</div>
            <p className="text-xs text-slate-500 mt-2">Rebalanceo automático FUND/UNIFIED activo</p>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-white/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Sectores Descubiertos</CardTitle>
            <Cpu className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <ul className="space-y-1 text-sm text-slate-300">
              {data.sectors.map((s) => (
                <li key={s.sector_name} className="flex justify-between">
                  <span>{s.sector_name}</span>
                  <span className={`text-xs uppercase ${s.status === "profitable" ? "text-emerald-400" : s.status === "failed" ? "text-red-400" : "text-amber-300"}`}>
                    {s.status}
                  </span>
                </li>
              ))}
              {data.sectors.length === 0 && <li className="text-slate-500">Sin sectores aún</li>}
            </ul>
          </CardContent>
        </Card>

        <Card className="bg-black/40 border-white/10 col-span-1 lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Configurar credenciales</CardTitle>
          </CardHeader>
          <CardContent className="grid md:grid-cols-4 gap-3">
            <input
              className="bg-slate-900 border border-white/10 rounded px-2 py-1 text-sm"
              placeholder="BYBIT_API_KEY"
              value={bybitKey}
              onChange={(e) => setBybitKey(e.target.value)}
            />
            <input
              className="bg-slate-900 border border-white/10 rounded px-2 py-1 text-sm"
              placeholder="BYBIT_API_SECRET"
              value={bybitSecret}
              onChange={(e) => setBybitSecret(e.target.value)}
            />
            <input
              className="bg-slate-900 border border-white/10 rounded px-2 py-1 text-sm"
              placeholder="BYBIT_MASTER_UID"
              value={bybitUid}
              onChange={(e) => setBybitUid(e.target.value)}
            />
            <input
              className="bg-slate-900 border border-white/10 rounded px-2 py-1 text-sm"
              placeholder="OLLAMA_URL"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
            />
            <button
              onClick={async () => {
                try {
                  await fetch(`${apiBase}/v1/secrets`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      BYBIT_API_KEY: bybitKey || undefined,
                      BYBIT_API_SECRET: bybitSecret || undefined,
                      BYBIT_MASTER_UID: bybitUid || undefined,
                      OLLAMA_URL: ollamaUrl || undefined,
                    }),
                  });
                  setBybitKey("");
                  setBybitSecret("");
                  setBybitUid("");
                  setOllamaUrl("");
                  loadStatus();
                } catch (err) {
                  console.error(err);
                }
              }}
              className="md:col-span-4 bg-blue-600 hover:bg-blue-700 text-white rounded px-3 py-2 text-sm font-semibold"
            >
              Guardar
            </button>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
