"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShieldAlert,
  Users,
  MapPin,
  Database,
  History,
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { name: "Moderation", href: "/admin/moderation", icon: ShieldAlert },
  { name: "User Management", href: "/admin/users", icon: Users },
  { name: "Resource Management", href: "/admin/resources", icon: MapPin },
  { name: "Data Ingestion", href: "/admin/ingestion", icon: Database },
  { name: "Audit Logs", href: "/admin/audit-logs", icon: History },
];

export default function Sidebar({
  closeMobileSidebar,
}: {
  closeMobileSidebar?: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 text-slate-200 flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <span className="font-bold text-lg text-sky-400">NBD Platform</span>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/admin" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={closeMobileSidebar}
              data-active={isActive ? "true" : undefined}
              className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                  : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
