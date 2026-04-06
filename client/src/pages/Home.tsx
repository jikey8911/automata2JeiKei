import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Coins, Cpu, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";

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
  const [showSecretsModal, setShowSecretsModal] = useState(false);
  const [supervisorLogs, setSupervisorLogs] = useState<string[]>([]);
  const [uaeLogs, setUaeLogs] = useState<string[]>([]);

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

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${apiBase.replace("/api", "")}/logs`); // supervisor container logs endpoint (exposed by Docker)
        if (res.ok) {
          const text = await res.text();
          const lines = text.split("\n").slice(-50).filter(Boolean);
          setSupervisorLogs(lines);
        }
      } catch (e) {
        console.error(e);
      }
    };
    fetchLogs();
    const id = setInterval(fetchLogs, 10000);
    return () => clearInterval(id);
  }, [apiBase]);

  useEffect(() => {
    const loadSecrets = async () => {
      try {
        const res = await fetch(`${apiBase}/v1/secrets`);
        const json = await res.json();
        setBybitKey(json.BYBIT_API_KEY || "");
        setBybitSecret(json.BYBIT_API_SECRET || "");
        setBybitUid(json.BYBIT_MASTER_UID || "");
        setOllamaUrl(json.OLLAMA_URL || "");
      } catch (err) {
        console.error(err);
      }
    };
    loadSecrets();
  }, [apiBase]);

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
          <CardHeader className="flex justify-between items-center">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Credenciales</CardTitle>
            <button
              onClick={() => setShowSecretsModal(true)}
              className="text-sm px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white"
            >
              Editar
            </button>
          </CardHeader>
          <CardContent>
            <p className="text-slate-400 text-sm">Configura API keys y OLLAMA_URL.</p>
          </CardContent>
        </Card>

        <div className="col-span-1 lg:col-span-3 grid md:grid-cols-2 gap-4">
          <Card className="bg-black/40 border-white/10">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-slate-400 uppercase">Logs Supervisor (docker logs)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
              {supervisorLogs.map((l, idx) => (
                <div key={idx} className="border-b border-white/5 pb-1 whitespace-pre-wrap">{l}</div>
              ))}
              {supervisorLogs.length === 0 && <div className="text-slate-500">Sin logs aún</div>}
            </CardContent>
          </Card>

          <Card className="bg-black/40 border-white/10">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-slate-400 uppercase">UAEs / actividad reciente</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-slate-300 max-h-64 overflow-y-auto">
              {data.containers.map((c) => (
                <div key={c.id} className="border-b border-white/5 pb-2">
                  <div className="flex justify-between text-sm">
                    <span>{c.name}</span>
                    <span className="text-emerald-400 uppercase">{c.status}</span>
                  </div>
                  <div className="text-slate-400">Última actividad: heartbeat reciente</div>
                </div>
              ))}
              {data.containers.length === 0 && <div className="text-slate-500">Sin UAEs</div>}
            </CardContent>
          </Card>
        </div>
      </main>

      {showSecretsModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-white/10 rounded-xl p-6 w-full max-w-3xl space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-lg font-semibold text-white">Credenciales</h2>
              <button onClick={() => setShowSecretsModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <input className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm" placeholder="BYBIT_API_KEY" value={bybitKey} onChange={(e) => setBybitKey(e.target.value)} />
              <input className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm" placeholder="BYBIT_API_SECRET" value={bybitSecret} onChange={(e) => setBybitSecret(e.target.value)} />
              <input className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm" placeholder="BYBIT_MASTER_UID" value={bybitUid} onChange={(e) => setBybitUid(e.target.value)} />
              <input className="bg-slate-800 border border-white/10 rounded px-2 py-2 text-sm" placeholder="OLLAMA_URL" value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} />
            </div>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowSecretsModal(false)} className="px-3 py-2 rounded border border-white/10 text-slate-300">Cancelar</button>
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
                    setShowSecretsModal(false);
                    loadStatus();
                  } catch (err) {
                    console.error(err);
                  }
                }}
                className="px-3 py-2 rounded bg-blue-600 hover:bg-blue-700 text-white"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
