import { useEffect, useState, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Trash2 } from "lucide-react";

type SubItem = {
  uid: string;
  username?: string;
  balance_usdt: number;
  uae_id?: string | null;
  status?: string;
  orphan: boolean;
};

const api = (path: string) => `${import.meta.env.VITE_API_URL?.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;

export default function Subaccounts() {
  const [items, setItems] = useState<SubItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(api("/subaccounts"));
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setItems(data.items || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (uid: string) => {
    if (!confirm(`Eliminar subcuenta ${uid}?`)) return;
    try {
      const res = await fetch(api(`/subaccounts/${uid}`), { method: "DELETE" });
      if (!res.ok) throw new Error(await res.text());
      await load();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Subcuentas Bybit</h1>
          <p className="text-sm text-slate-400">
            Saldo, estado y adopción por UAEs. Total: {items.length}
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Recargar
        </Button>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}
      {!loading && !error && items.length === 0 && (
        <div className="text-slate-300 text-sm">No hay subcuentas para mostrar.</div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((sub) => (
          <Card key={sub.uid} className="bg-slate-900 border-white/5">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-lg text-white">UID {sub.uid}</CardTitle>
              <div className="flex gap-2 items-center">
                {sub.orphan ? (
                  <Badge variant="secondary" className="bg-amber-500/20 text-amber-200">Huérfana</Badge>
                ) : (
                  <Badge variant="secondary" className="bg-emerald-500/20 text-emerald-200">En uso</Badge>
                )}
                <Button variant="ghost" size="icon" onClick={() => handleDelete(sub.uid)} title="Eliminar">
                  <Trash2 className="h-4 w-4 text-red-300" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-slate-200">
              <div className="text-sm">Username: {sub.username || "—"}</div>
              <div className="text-sm font-semibold">Balance: {sub.balance_usdt.toFixed(4)} USDT</div>
              <div className="text-sm">UAE asignada: {sub.uae_id || "Ninguna"}</div>
              <div className="text-xs text-slate-400">Estado: {sub.status || "free"}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
