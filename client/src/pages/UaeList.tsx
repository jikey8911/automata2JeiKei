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
  const [modal, setModal] = useState<{uaeId: string; masterUid?: string; subUid?: string; balance?: number} | null>(null);
  const [transferAmount, setTransferAmount] = useState<string>("");
  const [masterBalance, setMasterBalance] = useState<number>(0);

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

  const openTransferModal = async (uaeId: string, subUid?: string) => {
    setTransferAmount("");
    setModal({ uaeId, subUid, masterUid: undefined });
    try {
      const res = await fetch(`${apiBase}/v1/status`);
      if (res.ok) {
        const json = await res.json();
        const bal = json.genesis_balance?.USDT || 0;
        setMasterBalance(bal);
      }
    } catch (_) {}
  };

  const submitTransfer = async () => {
    if (!modal) return;
    const amount = parseFloat(transferAmount);
    if (isNaN(amount) || amount <= 0) {
      alert("Cantidad inválida");
      return;
    }
    try {
      const res = await fetch(`${apiBase}/v1/uae/transfer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uae_id: modal.uaeId, amount })
      });
      if (res.ok) {
        alert(`Transferencia de ${amount} USDT exitosa`);
        setModal(null);
        load();
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || "Fallo en la transferencia"}`);
      }
    } catch (_) {
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
                      <div className="flex items-center gap-2 min-w-[240px]">
                        {editingUae === uae.uae_id ? (
                          <div className="flex flex-col gap-1 w-full animate-in fade-in slide-in-from-top-1 duration-300">
                            <div className="flex items-center gap-2">
                              <select 
                                className="bg-slate-900 border border-white/20 rounded px-2 py-1.5 text-xs flex-1 outline-none focus:border-emerald-500 transition-colors"
                                defaultValue={uae.bybit_subaccount_id}
                                onChange={(e) => updateSubaccount(uae.uae_id, e.target.value)}
                              >
                                <option value={uae.bybit_subaccount_id}>{uae.bybit_subaccount_id} (Actual)</option>
                                {availableSubs.map(s => (
                                  <option key={s.uid} value={s.uid}>{s.username} ({s.uid})</option>
                                ))}
                                <option value="manual">✎ Escribir UID manualmente...</option>
                              </select>
                              <button 
                                onClick={() => setEditingUae(null)} 
                                className="p-1.5 text-slate-500 hover:text-white bg-white/5 rounded-md"
                              >✕</button>
                            </div>
                            
                            {/* Input manual si se solicita */}
                            <div className="flex gap-1 mt-1">
                              <input 
                                type="text"
                                placeholder="Nuevo UID (e.g. 1928374)"
                                className="bg-emerald-500/10 border border-emerald-500/30 rounded px-2 py-1 text-xs flex-1 outline-none text-emerald-400 placeholder:text-emerald-900"
                                onKeyDown={(e) => {
                                  if (e.key === 'Enter') {
                                    updateSubaccount(uae.uae_id, (e.target as HTMLInputElement).value);
                                  }
                                }}
                              />
                            </div>
                          </div>
                        ) : (
                          <>
                            <span className="text-xs font-mono text-slate-400">
                              {uae.bybit_subaccount_id || "SIN ASIGNAR"}
                            </span>
                            <button 
                              onClick={() => {
                                setEditingUae(uae.uae_id);
                                loadAvailable();
                              }}
                              className="p-1 text-emerald-500 hover:text-emerald-400 opacity-0 group-hover:opacity-100 transition-all border border-emerald-500/20 rounded-md bg-emerald-500/5"
                              title="Editar Asignación"
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
                          onClick={() => openTransferModal(uae.uae_id, uae.bybit_subaccount_id)}
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

      {modal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-white/10 rounded-xl p-6 w-full max-width[480px] max-w-md space-y-4 shadow-xl shadow-emerald-500/10">
            <div className="flex justify-between items-center">
              <div>
                <h2 className="text-lg font-semibold text-white">Transferir fondos</h2>
                <p className="text-xs text-slate-400">UAE: {modal.uaeId}</p>
              </div>
              <button onClick={() => setModal(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="text-sm text-slate-300 space-y-1">
              <div>Balance master disponible: <span className="font-mono text-emerald-400">{masterBalance.toFixed(2)} USDT</span></div>
              <div>Sub UID destino: <span className="font-mono text-blue-300">{modal.subUid || "N/D"}</span></div>
              <div>Master UID (env): <span className="font-mono text-slate-400">{process.env.BYBIT_MASTER_UID || "config secret"}</span></div>
            </div>
            <div className="space-y-2">
              <label className="text-xs text-slate-400">Monto (USDT)</label>
              <input 
                type="number"
                min="0"
                step="0.01"
                value={transferAmount}
                onChange={(e) => setTransferAmount(e.target.value)}
                className="w-full bg-slate-800 border border-white/10 rounded px-3 py-2 text-sm text-white focus:border-emerald-500 outline-none"
                placeholder="Ej: 10.0"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button onClick={() => setModal(null)} className="px-3 py-2 rounded border border-white/10 text-slate-300">Cancelar</button>
              <button onClick={submitTransfer} className="px-3 py-2 rounded bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold">Transferir</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

