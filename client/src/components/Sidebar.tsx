import { Link, useRoute } from "wouter";
import { Home, Cpu, Grid } from "lucide-react";

const links = [
  { href: "/", label: "Home", icon: Home },
  { href: "/uaes", label: "UAEs", icon: Cpu },
  { href: "/sectors", label: "Estrategias", icon: Grid },
];

export function Sidebar() {
  return (
    <aside className="w-52 bg-slate-950 border-r border-white/10 min-h-screen p-4 space-y-3 sticky top-0">
      <div className="text-lg font-bold text-blue-400">AUTOMATA</div>
      <nav className="space-y-2">
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
                <span className="text-sm">{l.label}</span>
              </div>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
