"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  Building2,
  BriefcaseBusiness,
  Users,
  ListTodo,
  Blocks,
  Boxes,
  FileText,
  GitBranch,
  LayoutDashboard,
  Mail,
  Menu,
  Network,
  Phone,
  Search,
  Settings2,
  Sun,
  Ticket,
  Upload,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "./ui/Button";
import { FormInput } from "./ui/Input";
import { State } from "./common";
import { Wordmark } from "./wordmark";
const groups = [
  {
    label: "Workspace",
    items: [
      { href: "/", label: "Overview", icon: LayoutDashboard },
      { href: "/graph", label: "Graph explorer", icon: Network },
      { href: "/entities", label: "Entities", icon: Boxes },
      { href: "/tickets", label: "Tickets", icon: Ticket },
      { href: "/properties", label: "Properties", icon: Building2 },
      { href: "/landlords", label: "Landlords", icon: Users },
      {
        href: "/providers",
        label: "Service providers",
        icon: BriefcaseBusiness,
      },
      { href: "/documents", label: "Documents", icon: FileText },
      { href: "/search", label: "Search", icon: Search },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/calls", label: "Calls", icon: Phone },
      { href: "/emails", label: "Emails", icon: Mail },
      { href: "/actions", label: "Change log", icon: FileText },
      { href: "/unallocated", label: "Unallocated ledger", icon: ListTodo },
      { href: "/ingestion", label: "Ingestion", icon: Upload },
    ],
  },
  {
    label: "Configure",
    items: [
      { href: "/rules", label: "Edge rules", icon: GitBranch },
      { href: "/schema", label: "Entity types", icon: Blocks },
      { href: "/settings", label: "Settings", icon: Settings2 },
    ],
  },
];
export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [mobile, setMobile] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const session = useQuery<{ authenticated: boolean }>({
    queryKey: ["session"],
    queryFn: async () => {
      const result = await fetch("/api/session");
      if (!result.ok) throw new Error("Cannot check session");
      return result.json();
    },
  });
  useEffect(() => {
    const stored = localStorage.getItem("propadmin-theme");
    document.documentElement.classList.toggle(
      "dark",
      stored === "dark" ||
        (!stored && matchMedia("(prefers-color-scheme: dark)").matches),
    );
  }, []);
  async function signIn(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.detail ?? "Sign in failed");
      setPassword("");
      await session.refetch();
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error("Sign in failed"));
    } finally {
      setBusy(false);
    }
  }
  function toggleTheme() {
    const dark = document.documentElement.classList.toggle("dark");
    localStorage.setItem("propadmin-theme", dark ? "dark" : "light");
    window.dispatchEvent(new Event("propadmin-theme"));
  }
  if (session.isPending || session.error)
    return (
      <div className="auth">
        <State
          pending={session.isPending}
          error={session.error}
          retry={() => void session.refetch()}
        />
      </div>
    );
  if (!session.data?.authenticated)
    return (
      <main className="auth">
        <div className="login">
          <Wordmark />
          <h1>
            Your property operations,
            <br />
            connected.
          </h1>
          <form onSubmit={signIn} className="form">
            <FormInput
              label="Admin password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <State error={error} />
            <Button loading={busy} type="submit">
              Sign in <ArrowUpRight size={16} />
            </Button>
          </form>
          <p className="caption">Private workspace · Administrator access</p>
        </div>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className={mobile ? "sidebar mobile-open" : "sidebar"}>
        <div className="sidebar-brand">
          <Wordmark />
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close navigation"
            className="mobile-only"
            onClick={() => setMobile(false)}
          >
            <X />
          </Button>
        </div>
        <nav aria-label="Main navigation">
          {groups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p className="nav-label">{group.label}</p>
              {group.items.map((item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`nav-link draw-underline ${active ? "active" : ""}`}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setMobile(false)}
                  >
                    <item.icon size={17} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="caption">Properly · Operations</span>
          <div className="actions">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label="Toggle colour theme"
              onClick={toggleTheme}
            >
              <Sun />
            </Button>
            <Button
              variant="ghost"
              onClick={async () => {
                await fetch("/api/session", { method: "DELETE" });
                await session.refetch();
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <div className="topbar">
          <div className="actions">
            <Button
              variant="ghost"
              size="icon"
              className="mobile-only"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu />
            </Button>
            <span>Property operations</span>
            <span className="topbar-divider">/</span>
            <span className="caption">
              {groups
                .flatMap((g) => g.items)
                .find(
                  (item) => item.href !== "/" && pathname.startsWith(item.href),
                )?.label ?? "Overview"}
            </span>
          </div>
          <Link className="draw-underline topbar-search" href="/search">
            <Search size={16} /> Search workspace <kbd>/</kbd>
          </Link>
        </div>
        <main className="main-content">{children}</main>
        <footer className="workspace-footer">
          Connected knowledge. Accountable actions.
        </footer>
      </div>
    </div>
  );
}
