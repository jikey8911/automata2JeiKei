import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import UaeList from "./pages/UaeList";
import Sectors from "./pages/Sectors";
import Settings from "./pages/Settings";
import { Sidebar } from "./components/Sidebar";
import { SystemProvider } from "jeikei-design-system";

function Router() {
  return (
      <Switch>
        <Route path="/" component={Home} />
        <Route path="/uaes" component={UaeList} />
        <Route path="/sectors" component={Sectors} />
        <Route path="/settings" component={Settings} />
        <Route path="/404" component={NotFound} />
        <Route component={NotFound} />
      </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <SystemProvider>
        <ThemeProvider defaultTheme="dark">
          <TooltipProvider>
            <Toaster />
            <div className="flex min-h-screen bg-slate-950 text-white">
              <Sidebar />
              <div className="flex-1">
                <Router />
              </div>
            </div>
          </TooltipProvider>
        </ThemeProvider>
      </SystemProvider>
    </ErrorBoundary>
  );
}

export default App;
