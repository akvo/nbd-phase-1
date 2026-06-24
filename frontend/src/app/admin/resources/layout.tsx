"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, MapPin, History, Users } from "lucide-react";

const sidebarItems = [
  { name: "User Management", href: "/admin/resources/users", icon: Users },
  { name: "Form Management", href: "/admin/resources/forms", icon: FileText },
  { name: "Site Management", href: "/admin/resources/sites", icon: MapPin },
  { name: "Activity Log", href: "/admin/resources/activity", icon: History },
];

export default function ResourceManagementLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex gap-6 min-h-[calc(100vh-16rem)]">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0">
        <nav className="space-y-1">
          {sidebarItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-sky-50 text-sky-700 border border-sky-200"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-transparent"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
