"use client";

import React, { useState, useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import Header from "@/components/admin/header";
import Tabs from "@/components/admin/tabs";
import {
  Download,
  Plus,
  ChevronDown,
  ClipboardList,
  MapPin,
  UserPlus,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading: authLoading, isAdmin } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [forms, setForms] = useState<any[]>([]);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Redirect non-admins away from admin-only routes
  useEffect(() => {
    if (!authLoading && user) {
      const adminOnlyRoutes = [
        "/admin/users",
        "/admin/sites",
        "/admin/audit-logs",
      ];
      if (
        adminOnlyRoutes.some((route) => pathname.startsWith(route)) &&
        !isAdmin
      ) {
        router.push("/admin/data");
      }
    }
  }, [pathname, user, authLoading, isAdmin, router]);

  useEffect(() => {
    apiClient
      .get("/forms")
      .then((res) => {
        if (res.data && res.data.length > 0) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fetched = res.data.map((f: any) => ({
            id: String(f.id),
            name: f.name,
          }));
          setForms(fetched);
        }
      })
      .catch(() => {
        // Fallback placeholder in case database is empty or down
        setForms([]);
      });
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Dynamic Page Title & Subtitle based on the active tab/route
  let title = "Admin Dashboard";
  let subtitle = "Nile Basin Discourse platform administrative workspace";
  let showBadge = false;
  const badgeLabel = "240 instances";
  let isTabbedRoute = false;

  if (pathname === "/admin/data") {
    title = "Data overview";
    subtitle =
      "Search and filter across all submitted data • Click a row to review";
    showBadge = true;
    isTabbedRoute = true;
  } else if (
    pathname === "/admin/sites" ||
    pathname.startsWith("/admin/sites/")
  ) {
    title = "Resource management";
    subtitle = "Manage forms, users, and platform settings";
    isTabbedRoute = true;
  }

  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Global Navigation Bar */}
      <Header />

      {/* Main Administrative Container */}
      <div className="flex-1 w-full px-8 py-8 space-y-6">
        {/* Title, Badges, and Action Buttons Row */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
              {showBadge && (
                <span className="bg-sky-50 text-sky-500 text-xs font-semibold px-2.5 py-0.5 rounded-full border border-sky-100">
                  {badgeLabel}
                </span>
              )}
            </div>
            <p className="text-slate-500 text-sm">{subtitle}</p>
          </div>

          {/* Action buttons - Site Management page */}
          {pathname === "/admin/sites/documents" && (
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => {
                  window.dispatchEvent(new CustomEvent("open-add-site-modal"));
                }}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition-colors shadow-sm cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <MapPin className="w-4 h-4" />
                <span>Add site</span>
              </button>
            </div>
          )}

          {/* Action buttons - User Management page */}
          {pathname === "/admin/sites/users" && (
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={() => {
                  window.dispatchEvent(
                    new CustomEvent("open-invite-user-modal")
                  );
                }}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition-colors shadow-sm cursor-pointer"
              >
                <UserPlus className="w-4 h-4" />
                <span>Invite user</span>
              </button>
            </div>
          )}

          {/* Action buttons (CSV Download & Add new) - Only on Data overview page */}
          {pathname === "/admin/data" && (
            <div
              className="flex items-center space-x-3 relative"
              ref={dropdownRef}
            >
              <button
                type="button"
                className="inline-flex items-center space-x-2 px-4 py-2 border border-slate-200 bg-white rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm cursor-pointer"
              >
                <Download className="w-4 h-4 text-slate-500" />
                <span>Download CSV</span>
              </button>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition-colors shadow-sm cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add new</span>
                  <ChevronDown className="w-4 h-4 opacity-80" />
                </button>

                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl border border-slate-200 shadow-lg py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                    <div className="px-3 py-1.5 text-xs font-semibold text-slate-400 border-b border-slate-100 mb-1">
                      Choose Ingestion Form
                    </div>
                    {forms.map((form) => (
                      <button
                        key={form.id}
                        type="button"
                        onClick={() => {
                          setDropdownOpen(false);
                          router.push(`/admin/data/new/${form.id}`);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors flex items-center space-x-2 cursor-pointer"
                      >
                        <ClipboardList className="w-4 h-4 text-slate-400" />
                        <span className="truncate">{form.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sub-Navigation Section Tabs - Only shown on tabbed routes */}
        {isTabbedRoute && <Tabs />}

        {/* Dynamic Nested Sub-view Viewport */}
        <main className="w-full">{children}</main>
      </div>
    </div>
  );
}
