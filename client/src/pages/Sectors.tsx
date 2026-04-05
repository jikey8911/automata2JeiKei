import { useEffect, useMemo, useState } from "react";

type SectorInfo = { sector_name: string; discoverer_uae_id: string; status: string; created_at: string };

export default function Sectors() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [sectors, setSectors] = useState<SectorInfo[]>([]);

  const load = async () => {
    const res = await fetch(`${apiBase}/v1/status`);
    const json = await res.json();
    setSectors(json.sectors || []);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="p-6 text-white">
      <h1 className="text-xl font-semibold mb-4">Estrategias / Sectores</h1>
      <ul className="space-y-2 text-sm">
        {sectors.map((s) => (
          <li key={s.sector_name} className="flex justify-between border border-white/10 rounded px-3 py-2">
            <span>{s.sector_name}</span>
            <span className={`uppercase ${s.status === "profitable" ? "text-emerald-400" : s.status === "failed" ? "text-red-400" : "text-amber-300"}`}>
              {s.status}
            </span>
          </li>
        ))}
        {sectors.length === 0 && <li className="text-slate-500">Sin sectores aún</li>}
      </ul>
    </div>
  );
}
