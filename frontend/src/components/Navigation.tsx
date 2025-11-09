import { NavLink as RouterNavLink } from "react-router-dom";
import { MessageSquare, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

const Navigation = () => {
  return (
    <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50">
      <div className="glass rounded-full p-2 flex gap-2">
        <RouterNavLink
          to="/"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2 px-6 py-3 rounded-full transition-all",
              isActive
                ? "bg-gradient-to-br from-primary to-primary-glow text-primary-foreground shadow-[0_0_20px_rgba(0,150,255,0.5)]"
                : "text-muted-foreground hover:text-foreground"
            )
          }
        >
          <Mic className="w-5 h-5" />
          <span className="font-medium">Voice</span>
        </RouterNavLink>
        <RouterNavLink
          to="/chat"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2 px-6 py-3 rounded-full transition-all",
              isActive
                ? "bg-gradient-to-br from-primary to-primary-glow text-primary-foreground shadow-[0_0_20px_rgba(0,150,255,0.5)]"
                : "text-muted-foreground hover:text-foreground"
            )
          }
        >
          <MessageSquare className="w-5 h-5" />
          <span className="font-medium">Chat</span>
        </RouterNavLink>
      </div>
    </nav>
  );
};

export default Navigation;
