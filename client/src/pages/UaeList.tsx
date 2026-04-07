import { useEffect, useMemo, useState } from "react";

type UaeRegistryEntry = {
  uae_id: string;
  bybit_subaccount_id: string;
  vcc_card_id: string;
  status: string;
  created_at: string;
  balance?: number;
};

type AvailableSubaccount = {
  uid: string;
  username: string;
};

export default function UaeList() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_URL || "/api", []);
  const [uaes, setUaes] = useState<UaeRegistryEntry[]>([]);
  const [availableSubs, setAvailableSubs] = useState<AvailableSubaccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingUae, setEditingUae] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      // CORRECCIÓN: El endpoint es /v1/uae/list y devuelve { uaes: [...] }
      const res = await fetch(`${apiBase}/v1/uae/list`);
      if (res.ok) {
        const json = await res.json();
        setUaes(json.uaes || []);
      }
    } catch (e) {
      console.error("Failed to fetch UAEs", e);
    } finally {
      setLoading(false);
    }
  };

  const loadAvailable = async () => {
    try {
      const res = await fetch(`${apiBase}/v1/uae/available_subaccounts`);
      if (res.ok) {
        const json = await res.json();
        setAvailableSubs(json.available || []);
      }
    } catch (e) {
      console.error("Failed to fetch available subs", e);
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

  const handleDeleteRegistry = async (uaeId: string) => {
    if (!window.confirm(`¿Seguro que quieres borrar el REGISTRO de ${uaeId}? \nEsto NO borra la subcuenta en Bybit, solo el vínculo local.`)) {
      return;
    }

    try {
      const res = await fetch(`${apiBase}/v1/uae/registry/${uaeId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        alert("Registro eliminado");
        load();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Fallo al borrar"}`);
      }
    } catch (e) {
      alert("Error de conexión");
    }
  };

  const updateSubaccount = async (uaeId: string, newSubUid: string) => {
    try {
      const res = await fetch(`${apiBase}/v1/uae/registry/subaccount/${uaeId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sub_uid: newSubUid })
      });
      if (res.ok) {
        setEditingUae(null);
        load();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Fallo al actualizar"}`);
      }
    } catch (e) {
      alert("Error de conexión");
    }
  };

  useEffect(() => {
    load();
    loadAvailable();
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
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 min-w-[200px]">
                        {editingUae === uae.uae_id ? (
                          <div className="flex items-center gap-2 w-full">
                            <select 
                              className="bg-slate-900 border border-white/20 rounded px-2 py-1 text-xs w-full outline-none focus:border-blue-500"
                              defaultValue={uae.bybit_subaccount_id}
                              onChange={(e) => updateSubaccount(uae.uae_id, e.target.value)}
                            >
                              <option value={uae.bybit_subaccount_id}>{uae.bybit_subaccount_id} (Actual)</option>
                              {availableSubs.map(s => (
                                <option key={s.uid} value={s.uid}>{s.username} ({s.uid})</option>
                              ))}
                            </select>
                            <button onClick={() => setEditingUae(null)} className="text-slate-500 hover:text-white">✕</button>
                          </div>
                        ) : (
                          <>
                            <span className="text-xs font-mono text-slate-400">
                              {uae.bybit_subaccount_id}
                            </span>
                            <button 
                              onClick={() => {
                                setEditingUae(uae.uae_id);
                                loadAvailable();
                              }}
                              className="p-1 text-blue-500 hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-all border border-blue-500/20 rounded"
                              title="Cambiar Subcuenta"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                            </button>
                          </>
                        )}
                      </div>
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
                      <div className="flex justify-end items-center gap-3">
                        <button 
                          onClick={() => handleTransfer(uae.uae_id)}
                          className="px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold rounded shadow-lg shadow-emerald-500/20 transition-all active:scale-95"
                        >
                          FONDER
                        </button>
                        <button 
                          onClick={() => handleDeleteRegistry(uae.uae_id)}
                          title="Borrar Registro"
                          className="p-1.5 text-slate-600 hover:text-rose-500 hover:bg-rose-500/10 rounded transition-all"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </div>
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

