import { Link, useRoute } from "wouter";
import { Home, Cpu, Grid, Settings, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

const links = [
  { href: "/", label: "Home", icon: Home },
  { href: "/uaes", label: "UAEs", icon: Cpu },
  { href: "/sectors", label: "Estrategias", icon: Grid },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <aside
      className={`${
        collapsed ? "w-16" : "w-52"
      } bg-slate-950 border-r border-white/10 min-h-screen p-4 space-y-3 sticky top-0 flex flex-col transition-all duration-200`}
    >
      <div className="flex items-center justify-between">
        {!collapsed && <div className="text-lg font-bold text-blue-400">AUTOMATA</div>}
        <button
          className="text-slate-400 hover:text-white"
          onClick={() => setCollapsed((v) => !v)}
          aria-label="Toggle sidebar"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      <nav className="space-y-2 flex-1">
        {links.map((l) => {
          const [isActive] = useRoute(l.href);
          const Icon = l.icon;
          return (
            <Link key={l.href} href={l.href} className="block">
              <div
                className={`flex items-center gap-2 px-3 py-2 rounded ${
                  isActive ? "bg-blue-600/30 text-white" : "text-slate-300 hover:bg-white/5"
                }`}
              >
                <Icon className="h-4 w-4" />
                {!collapsed && <span className="text-sm">{l.label}</span>}
              </div>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto">
        <Link href="/settings" className="block">
          <div
            className={`flex items-center gap-2 px-3 py-2 rounded ${
              useRoute("/settings")[0] ? "bg-blue-600/30 text-white" : "text-slate-300 hover:bg-white/5"
            }`}
          >
            <Settings className="h-4 w-4" />
            {!collapsed && <span className="text-sm">Credenciales</span>}
          </div>
        </Link>
      </div>
    </aside>
  );
}
