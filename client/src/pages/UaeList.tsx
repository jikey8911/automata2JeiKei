import { useEffect, useMemo, useState } from "react";

type ContainerInfo = { name: string; status: string; id: string };

export default function UaeList() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [containers, setContainers] = useState<ContainerInfo[]>([]);

  const load = async () => {
    const res = await fetch(`${apiBase}/v1/status`);
    const json = await res.json();
    setContainers(json.containers || []);
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="p-6 text-white">
      <h1 className="text-xl font-semibold mb-4">UAEs</h1>
      <ul className="space-y-2 text-sm">
        {containers.map((c) => (
          <li key={c.id} className="flex justify-between border border-white/10 rounded px-3 py-2">
            <span>{c.name}</span>
            <span className="text-emerald-400 uppercase">{c.status}</span>
          </li>
        ))}
        {containers.length === 0 && <li className="text-slate-500">Sin UAEs</li>}
      </ul>
    </div>
  );
}
