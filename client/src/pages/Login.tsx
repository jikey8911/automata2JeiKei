import React, { useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { API_BASE_URL } from "@/const";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2, Lock, User } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [, setLocation] = useLocation();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        await login(data.access_token);
        toast.success("Bienvenido de nuevo a AutomataAI");
        setLocation("/");
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || "Credenciales incorrectas");
      }
    } catch (error) {
      console.error("Error en login:", error);
      toast.error("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900 via-slate-950 to-black p-4">
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none"></div>
      
      <Card className="w-full max-w-md border-white/10 bg-black/40 backdrop-blur-xl shadow-2xl relative overflow-hidden group">
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500 to-emerald-500 rounded-lg blur opacity-10 group-hover:opacity-20 transition duration-1000 group-hover:duration-200"></div>
        
        <CardHeader className="space-y-1 text-center relative">
          <div className="mx-auto w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mb-4 border border-blue-500/30">
            <span className="text-3xl">⚙️</span>
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight text-white font-mono uppercase">Automata AI</CardTitle>
          <CardDescription className="text-slate-400">
            Fase 3: Ejecución Real - Centro de Mando
          </CardDescription>
        </CardHeader>
        
        <CardContent className="relative">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-slate-300 text-xs font-semibold uppercase tracking-wider">Usuario</Label>
              <div className="relative">
                <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <Input
                  id="username"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:border-blue-500/50 focus:ring-blue-500/20"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-300 text-xs font-semibold uppercase tracking-wider">Contraseña</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 bg-white/5 border-white/10 text-white placeholder:text-slate-600 focus:border-blue-500/50 focus:ring-blue-500/20"
                  required
                />
              </div>
            </div>
            
            <Button 
              type="submit" 
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-6 rounded-xl transition-all shadow-lg shadow-blue-500/20 border-t border-white/10"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  AUTENTICANDO...
                </>
              ) : (
                "ACCEDER AL SISTEMA"
              )}
            </Button>
          </form>
        </CardContent>
        
        <CardFooter className="flex flex-col space-y-4 border-t border-white/5 pt-6 relative">
          <div className="text-center text-xs text-slate-500">
            Protegido por cifrado de extremo a extremo
          </div>
          <div className="text-[10px] text-slate-700 font-mono">
            SISTEMA JEIKEI v3.2.0-STABLE
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
