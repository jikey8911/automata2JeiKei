import { useEffect, useMemo, useState } from "react";

type UaeRegistryEntry = {
  uae_id: string;
  bybit_subaccount_id: string;
  vcc_card_id: string;
  status: string;
  created_at: string;
  balance?: number;
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

  const handleTransfer = async (uaeId: string) => {
    const amountStr = window.prompt("Cantidad a transferir (USDT):", "10.0");
    if (!amountStr) return;
    
    const amount = parseFloat(amountStr);
    if (isNaN(amount) || amount <= 0) {
      alert("Cantidad inválida");
      return;
    }

    try {
      const res = await fetch(`${apiBase}/v1/uae/transfer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uae_id: uaeId, amount })
      });
      
      if (res.ok) {
        alert(`Transferencia de ${amount} USDT exitosa`);
        load();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Fallo en la transferencia"}`);
      }
    } catch (e) {
      alert("Error de conexión");
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
          className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-all text-sm flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Refrescar Datos
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {loading ? (
          <div className="text-center py-20 text-slate-500 animate-pulse font-mono tracking-tighter">
            CONSULTANDO ORÁCULO DE BALANCE...
          </div>
        ) : uaes.length === 0 ? (
          <div className="bg-white/5 border border-dashed border-white/10 rounded-2xl py-20 text-center">
            <p className="text-slate-500 italic">No hay Agentes registrados en el ecosistema.</p>
          </div>
        ) : (
          <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden backdrop-blur-xl shadow-2xl shadow-emerald-500/5">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white/5 text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-6 py-4 font-semibold">Identificador UAE</th>
                  <th className="px-6 py-4 font-semibold">Sub-UID</th>
                  <th className="px-6 py-4 font-semibold text-right">Saldo (USDT)</th>
                  <th className="px-6 py-4 font-semibold text-center">Estado</th>
                  <th className="px-6 py-4 font-semibold text-right">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {uaes.map((uae) => (
                  <tr key={uae.uae_id} className="hover:bg-white/[0.02] transition-colors group">
                    <td className="px-6 py-4">
                      <div className="font-mono text-emerald-400 font-bold">{uae.uae_id}</div>
                      <div className="text-[10px] text-slate-500 font-mono opacity-50">
                        {new Date(uae.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-mono text-slate-400">
                      {uae.bybit_subaccount_id}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="font-mono text-lg text-white font-medium">
                        {uae.balance?.toFixed(2) || "0.00"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                        uae.status === 'active' 
                        ? 'bg-emerald-400/10 text-emerald-400 border-emerald-400/20' 
                        : 'bg-slate-400/10 text-slate-400 border-slate-400/20'
                      }`}>
                        {uae.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => handleTransfer(uae.uae_id)}
                        className="px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold rounded shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
                      >
                        FONDER
                      </button>
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

