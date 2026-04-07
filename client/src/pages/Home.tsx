import { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";
import { NeoButton, NeoCard, NeoGrid, NeoPanel } from "jeikei-design-system";

type ContainerInfo = { name: string; status: string; id: string };
type SectorInfo = { sector_name: string; discoverer_uae_id: string; status: string; created_at: string };
type StatusPayload = { containers: ContainerInfo[]; sectors: SectorInfo[]; genesis_balance: Record<string, number> };
type HealthPayload = {
  supervisor: boolean;
  docker: boolean;
  wallet: boolean;
  wallet_error?: string;
  ollama: boolean;
  ollama_models?: string[];
};

export default function Home() {
  const [data, setData] = useState<StatusPayload>({ containers: [], sectors: [], genesis_balance: {} });
  const [loading, setLoading] = useState(false);
  const [showContainers, setShowContainers] = useState(false);
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [supervisorLogs, setSupervisorLogs] = useState<string[]>([]);
  const [uaeLogs, setUaeLogs] = useState<string[]>([]);
  const [health, setHealth] = useState<HealthPayload | null>(null);

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
    const id = setInterval(loadStatus, 40000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const loadHealth = async () => {
      try {
        const res = await fetch(`${apiBase}/v1/health`);
        const json = await res.json();
        setHealth(json);
      } catch (err) {
        console.error(err);
      }
    };
    loadHealth();
    const id = setInterval(loadHealth, 7000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch(`${apiBase}/v1/logs`);
        if (res.ok) {
          const text = await res.text();
          const lines = text.split("\n").slice(-50).filter(Boolean);
          setSupervisorLogs(lines);
        }
      } catch (e) {
        // Mantener silencioso si el endpoint no está disponible
      }
    };
    fetchLogs();
    const id = setInterval(fetchLogs, 10000);
    return () => clearInterval(id);
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
        <NeoButton onClick={loadStatus} variant="primary" size="md" className="flex items-center gap-2">
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </NeoButton>
      </header>

      <main className="space-y-6">
        {/* Indicadores rápidos */}
        <div className="flex flex-wrap gap-3">
          {[
            { label: "Supervisor", ok: health?.supervisor ?? false },
            { label: "Docker", ok: health?.docker ?? false },
            { label: "Billetera", ok: health?.wallet ?? false, extra: health?.wallet_error },
            { label: "Ollama", ok: health?.ollama ?? false },
          ].map((item) => (
            <div
              key={item.label}
              className={`px-3 py-2 rounded-lg border text-sm ${
                item.ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200" : "border-red-500/30 bg-red-500/10 text-red-200"
              }`}
            >
              <span className="font-semibold">{item.label}:</span>{" "}
              <span>{item.ok ? "OK" : "OFF"}</span>
              {item.extra && !item.ok && <span className="block text-xs text-red-200/80 mt-1">{item.extra}</span>}
            </div>
          ))}
        </div>

        <NeoGrid columns={{ base: 1, md: 3 }} gap="md" className="w-full">
          <NeoCard
            title="UAEs Activos"
            value={data.containers.length}
            className="backdrop-blur border-white/10"
            glow
          >
            <div className="flex items-center justify-between mt-3 text-sm text-slate-300">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-emerald-400" />
                <span>{data.containers.length ? "Operando" : "Monitor esperando ignición"}</span>
              </div>
              <button
                onClick={() => setShowContainers((v) => !v)}
                className="text-xs flex items-center gap-1 text-blue-300"
              >
                {showContainers ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />} Detalle
              </button>
            </div>
            {showContainers && (
              <ul className="mt-3 space-y-1 text-sm text-slate-200">
                {data.containers.map((c) => (
                  <li key={c.id} className="flex justify-between">
                    <span>{c.name}</span>
                    <span className="text-emerald-400 uppercase text-xs">{c.status}</span>
                  </li>
                ))}
                {data.containers.length === 0 && <li className="text-slate-500">Sin UAEs (monitor lanzará UAE-Alpha)</li>}
              </ul>
            )}
          </NeoCard>

          <NeoCard title="Saldo Génesis (Bybit)" value={`${totalUSDT.toFixed(2)} USDT`} trend={`USDC ${totalUSDC.toFixed(2)}`} glow>
            <p className="text-xs text-slate-400 mt-3">Rebalanceo automático FUND/UNIFIED activo</p>
          </NeoCard>

          <NeoCard title="Sectores Descubiertos" value={data.sectors.length} trend="Estado evolutivo" glow={false}>
            <ul className="space-y-1 text-sm text-slate-200 mt-3">
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
          </NeoCard>
        </NeoGrid>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <NeoPanel glow className="border-white/10">
            <p className="text-xs uppercase text-slate-400 mb-3">Logs Supervisor</p>
            <div className="space-y-1 text-xs text-slate-200 max-h-64 overflow-y-auto">
              {supervisorLogs.map((l, idx) => (
                <div key={idx} className="border-b border-white/5 pb-1 whitespace-pre-wrap">{l}</div>
              ))}
              {supervisorLogs.length === 0 && <div className="text-slate-500">Sin logs aún</div>}
            </div>
          </NeoPanel>

          <NeoPanel className="border-white/10">
            <p className="text-xs uppercase text-slate-400 mb-3">Logs UAEs / actividad</p>
            <div className="space-y-1 text-xs text-slate-200 max-h-64 overflow-y-auto">
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
            </div>
          </NeoPanel>
        </div>
      </main>

    </div>
  );
}
