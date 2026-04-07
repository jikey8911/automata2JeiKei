import { useEffect, useMemo, useState } from "react";

type UaeRegistryEntry = {
  uae_id: string;
  bybit_subaccount_id: string;
  vcc_card_id: string;
  status: string;
  created_at: string;
};

export default function UaeList() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [uaes, setUaes] = useState<UaeRegistryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/v1/uaes`);
      if (res.ok) {
        const json = await res.json();
        setUaes(json);
      }
    } catch (e) {
      console.error("Failed to fetch UAEs", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="p-8 text-slate-200">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            UAE Registry
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Gobernanza de Agentes Autónomos y Subcuentas Financieras
          </p>
        </div>
        <button 
          onClick={load}
          className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-sm"
        >
          Refrescar
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="text-center py-20 text-slate-500 animate-pulse">Consultando oráculo de registro...</div>
        ) : uaes.length === 0 ? (
          <div className="bg-white/5 border border-dashed border-white/10 rounded-2xl py-20 text-center">
            <p className="text-slate-500 italic">No hay Agentes registrados en el ecosistema.</p>
          </div>
        ) : (
          <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-xl">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-6 py-4 font-semibold">Identificador UAE</th>
                  <th className="px-6 py-4 font-semibold">Bybit Sub-UID</th>
                  <th className="px-6 py-4 font-semibold">VCC ID</th>
                  <th className="px-6 py-4 font-semibold text-right">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {uaes.map((uae) => (
                  <tr key={uae.uae_id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-mono text-emerald-400">{uae.uae_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono opacity-50">
                        {new Date(uae.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-slate-800 rounded font-mono text-xs text-slate-300">
                        {uae.bybit_subaccount_id}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-400 font-mono text-xs">
                      {uae.vcc_card_id}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        uae.status === 'active' 
                        ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' 
                        : 'bg-slate-400/10 text-slate-400 border-slate-400/20'
                      }`}>
                        {uae.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

