import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Loader2, LogOut, Settings, Activity, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Loader2 className="animate-spin text-blue-500 h-10 w-10" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <header className="flex justify-between items-center mb-8 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-2xl font-bold font-mono tracking-tighter text-blue-400">AUTOMATA AI</h1>
          <p className="text-slate-400 text-sm">Panel de Control de Agente Autónomo</p>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex flex-col items-end">
            <span className="text-sm font-semibold">{user?.full_name || user?.username}</span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="h-3 w-3" /> VERIFICADO
            </span>
          </div>
          <Button variant="ghost" size="icon" onClick={logout} className="hover:bg-red-500/10 hover:text-red-400 border border-white/5">
            <LogOut className="h-5 w-5" />
          </Button>
        </div>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Estado del Agente</CardTitle>
            <Activity className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">ACTIVO</div>
            <p className="text-xs text-slate-500 mt-1">Sincronizado con Binance API</p>
          </CardContent>
        </Card>

        {/* Placeholder para más métricas */}
        <Card className="bg-black/40 border-white/10 backdrop-blur-md">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 uppercase">Configuración</CardTitle>
            <Settings className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-300">MODO PRO</div>
            <p className="text-xs text-slate-500 mt-1">Fase 3: Ejecución Real</p>
          </CardContent>
        </Card>
      </main>

      <div className="mt-8 p-12 border-2 border-dashed border-white/5 rounded-3xl flex flex-col items-center justify-center text-slate-600 italic">
        "La autonomía no es solo automatización, es inteligencia aplicada al valor."
      </div>
    </div>
  );
}
