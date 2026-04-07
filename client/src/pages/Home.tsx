import { useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw, ChevronDown, ChevronRight } from "lucide-react";
import { NeoLayout, NeoButton, NeoCard, NeoGrid, NeoPanel } from "jeikei-design-system";

type ContainerInfo = { name: string; status: string; id: string };
type SectorInfo = { sector_name: string; discoverer_uae_id: string; status: string; created_at: string };
type StatusPayload = { containers: ContainerInfo[]; sectors: SectorInfo[]; genesis_balance: Record<string, number> };
type HealthPayload = {
  supervisor: boolean;
  docker: boolean;
  wallet: boolean;
  wallet_error?: string;
  ollama: boolean;
};

export default function Home() {
  const [data, setData] = useState<StatusPayload>({ containers: [], sectors: [], genesis_balance: {} });
  const [loading, setLoading] = useState(false);
  const [showContainers, setShowContainers] = useState(false);
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [health, setHealth] = useState<HealthPayload | null>(null);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/v1/status`);
      setData(await res.json());
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
      const res = await fetch(`${apiBase}/v1/health`);
      setHealth(await res.json());
    };
    loadHealth();
    const id = setInterval(loadHealth, 7000);
    return () => clearInterval(id);
  }, []);

  const totalUSDT = data.genesis_balance["USDT"] || 0;
  const totalUSDC = data.genesis_balance["USDC"] || 0;

  return (
    <NeoLayout>
      <div className="space-y-10">

        {/* HEADER */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-black text-neo-accent tracking-widest">
              AUTOMATA SUPERVISOR
            </h1>
            <p className="jk-data-label text-neo-muted">
              Neural Monitoring Interface
            </p>
          </div>

          <NeoButton onClick={loadStatus} size="md">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </NeoButton>
        </div>

        {/* STATUS */}
        <NeoGrid columns={{ base: 2, md: 4 }} gap="sm">
          {[
            { label: "Supervisor", ok: health?.supervisor },
            { label: "Docker", ok: health?.docker },
            { label: "Wallet", ok: health?.wallet },
            { label: "Ollama", ok: health?.ollama },
          ].map((item) => (
            <NeoCard
              key={item.label}
              title={item.label}
              value={item.ok ? "ONLINE" : "OFFLINE"}
              glow={item.ok}
            />
          ))}
        </NeoGrid>

        {/* MAIN CARDS */}
        <NeoGrid columns={{ base: 1, md: 3 }} gap="lg">

          <NeoCard title="Active UAEs" value={data.containers.length.toString()} glow>
            <div className="flex justify-between items-center mt-4">
              <span className="jk-data-label">
                {data.containers.length ? "Running" : "Idle"}
              </span>

              <button onClick={() => setShowContainers(!showContainers)}>
                {showContainers ? <ChevronDown /> : <ChevronRight />}
              </button>
            </div>

            {showContainers && (
              <div className="mt-4 space-y-2">
                {data.containers.map((c) => (
                  <div key={c.id} className="jk-glass p-2 rounded">
                    <div className="flex justify-between">
                      <span>{c.name}</span>
                      <span className="text-neo-accent">{c.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </NeoCard>

          <NeoCard
            title="Genesis Balance"
            value={`${totalUSDT.toFixed(2)} USDT`}
            trend={`USDC ${totalUSDC.toFixed(2)}`}
          />

          <NeoCard title="Sectors" value={data.sectors.length.toString()}>
            <div className="mt-4 space-y-2">
              {data.sectors.map((s) => (
                <div key={s.sector_name} className="flex justify-between">
                  <span>{s.sector_name}</span>
                  <span className="text-neo-magenta">{s.status}</span>
                </div>
              ))}
            </div>
          </NeoCard>

        </NeoGrid>

        {/* LOGS */}
        <NeoGrid columns={{ base: 1, md: 2 }} gap="lg">

          <NeoPanel title="Supervisor Logs" glow>
            <div className="text-xs font-mono space-y-1 opacity-80 max-h-64 overflow-auto">
              <div>[SYSTEM] Awaiting logs...</div>
            </div>
          </NeoPanel>

          <NeoPanel title="UAE Activity">
            <div className="text-xs font-mono space-y-1 opacity-80 max-h-64 overflow-auto">
              {data.containers.length === 0 ? (
                <div className="opacity-40 text-center py-10">
                  <Activity className="mx-auto mb-2 opacity-30" />
                  Waiting for neural activity...
                </div>
              ) : (
                data.containers.map((c) => (
                  <div key={c.id} className="jk-glass p-2 rounded">
                    {c.name} :: {c.status}
                  </div>
                ))
              )}
            </div>
          </NeoPanel>

        </NeoGrid>

      </div>
    </NeoLayout>
  );
}