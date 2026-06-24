import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Moon, Sun, Circle, LogIn, LogOut, BarChart3, Library, MessageSquare } from "lucide-react";
import { Button } from "./ui";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { getHealth } from "@/services/api";
import type { HealthInfo } from "@/services/types";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Chat", icon: MessageSquare },
  { to: "/knowledge", label: "Knowledge Base", icon: Library },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
];

export function Topbar() {
  const { theme, toggle } = useTheme();
  const { username, logout } = useAuth();
  const { pathname } = useLocation();
  const [health, setHealth] = useState<HealthInfo | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
    const t = setInterval(() => getHealth().then(setHealth).catch(() => {}), 20000);
    return () => clearInterval(t);
  }, []);

  const online = health?.ollama_available;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
      <nav className="flex items-center gap-1">
        {NAV.map(({ to, label, icon: Icon }) => {
          const active = to === "/" ? pathname === "/" || pathname.startsWith("/c/") : pathname === to;
          return (
            <Link
              key={to}
              to={to}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                active ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-secondary"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground" title={online ? "Ollama connected" : "Ollama offline"}>
          <Circle className={cn("h-2.5 w-2.5", online ? "fill-green-500 text-green-500" : "fill-red-500 text-red-500")} />
          <span className="hidden md:inline">{health?.default_model ?? "model"}</span>
        </div>
        <Button variant="ghost" size="icon" onClick={toggle} title="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        {username ? (
          <div className="flex items-center gap-2">
            <span className="hidden text-sm text-muted-foreground sm:inline">{username}</span>
            <Button variant="ghost" size="icon" onClick={logout} title="Log out">
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Link to="/login">
            <Button variant="outline" size="sm">
              <LogIn className="h-4 w-4" /> Sign in
            </Button>
          </Link>
        )}
      </div>
    </header>
  );
}
