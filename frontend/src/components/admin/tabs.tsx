"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

interface TabItem {
  name: string;
  href: string;
  adminOnly?: boolean;
}

const tabItems: TabItem[] = [
  { name: "Data", href: "/admin/data" },
  { name: "User management", href: "/admin/users", adminOnly: true },
  { name: "Site management", href: "/admin/sites", adminOnly: true },
  { name: "Activity log", href: "/admin/audit-logs", adminOnly: true },
];

export default function Tabs() {
  const pathname = usePathname();
  const { isAdmin } = useAuth();

  return (
    <div className="flex border border-slate-200 rounded-lg p-0.5 bg-slate-100/50 w-fit">
      {tabItems.map((tab) => {
        const isActive = pathname === tab.href;
        const isLocked = tab.adminOnly && !isAdmin;

        if (isLocked) {
          return (
            <span
              key={tab.name}
              className="px-4 py-1.5 rounded-md text-xs font-semibold text-slate-400 cursor-not-allowed flex items-center space-x-1"
              title="Admin access required"
            >
              <Lock className="w-3 h-3" />
              <span>{tab.name}</span>
            </span>
          );
        }

        return (
          <Link
            key={tab.name}
            href={tab.href}
            data-active={isActive ? "true" : undefined}
            className={`px-4 py-1.5 rounded-md text-xs font-semibold transition-colors ${
              isActive
                ? "bg-slate-200 text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {tab.name}
          </Link>
        );
      })}
    </div>
  );
}
