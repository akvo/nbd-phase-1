"use client";

import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { apiClient } from "@/lib/api";
import { useTranslations } from "next-intl";

interface SiteHeaderProps {
  showActions?: boolean;
}

interface AuthUser {
  id: string;
  email: string;
  role: "Admin" | "Reviewer";
  display_name?: string | null;
  avatar_url?: string | null;
}

export function SiteHeader({ showActions = true }: SiteHeaderProps) {
  const t = useTranslations();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch current user for the public page (AuthContext skips non-admin routes)
  useEffect(() => {
    apiClient
      .get<AuthUser>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setUserLoading(false));
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!dropdownOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownOpen]);

  const handleSignOut = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore
    }
    setUser(null);
    setDropdownOpen(false);
    window.location.href = "/login";
  };

  const initials = user?.display_name
    ? user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : (user?.email?.slice(0, 2).toUpperCase() ?? "?");

  return (
    <header className="bg-white border-b border-grey-200 h-16 w-full flex items-center justify-between px-4 sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-2">
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => (window.location.href = "/")}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.svg"
            alt={t("header.brand")}
            className="h-10 w-10"
          />
          <div className="flex flex-col">
            <span className="text-base font-bold text-[#4a90c4] leading-tight">
              {t("header.brand")}
            </span>
            <span className="text-xs text-slate-500 leading-tight">
              {t("header.subtitle")}
            </span>
          </div>
        </div>
      </div>

      {showActions ? (
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          {userLoading ? null : user ? (
            /* ── Authenticated: avatar + dropdown ── */
            <div className="relative" ref={dropdownRef}>
              <button
                id="site-header-user-menu-btn"
                onClick={() => setDropdownOpen((prev) => !prev)}
                className="flex items-center gap-2 rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-nbd-primary/50 transition-opacity hover:opacity-80"
                aria-haspopup="true"
                aria-expanded={dropdownOpen}
                aria-label="User menu"
              >
                {user.avatar_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={user.avatar_url}
                    alt={user.display_name ?? user.email}
                    className="w-8 h-8 rounded-full object-cover border border-slate-200"
                  />
                ) : (
                  <span className="w-8 h-8 rounded-full bg-nbd-primary flex items-center justify-center text-white text-xs font-bold select-none">
                    {initials}
                  </span>
                )}
                <svg
                  className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-150 ${dropdownOpen ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>

              {dropdownOpen && (
                <div
                  id="site-header-user-dropdown"
                  className="absolute right-0 top-full mt-2 w-52 bg-white rounded-xl border border-slate-200 shadow-xl py-1.5 z-50 animate-fade-in"
                  role="menu"
                >
                  {/* User info */}
                  <div className="px-4 py-2.5 border-b border-slate-100">
                    <p className="text-xs font-semibold text-slate-800 truncate">
                      {user.display_name ?? user.email}
                    </p>
                    <p className="text-[10px] text-slate-400 truncate">
                      {user.email}
                    </p>
                  </div>

                  {/* Admin link — only for Admin role */}
                  {user.role === "Admin" && (
                    <a
                      href="/admin"
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                      role="menuitem"
                    >
                      <svg
                        className="w-4 h-4 text-slate-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                      </svg>
                      {t("common.adminPanel")}
                    </a>
                  )}

                  {/* Sign out */}
                  <button
                    id="site-header-sign-out-btn"
                    onClick={handleSignOut}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
                    role="menuitem"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                      />
                    </svg>
                    {t("common.signOut")}
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* ── Unauthenticated: Log in button ── */
            <Button
              variant="ghost"
              onClick={() => (window.location.href = "/login")}
            >
              {t("common.login")}
            </Button>
          )}
        </div>
      ) : (
        <button
          onClick={() => setIsMenuOpen(!isMenuOpen)}
          className="bg-white hover:bg-slate-100 p-2 rounded-lg text-nbd-text-dark transition-colors outline-none"
          aria-label="Toggle menu"
        >
          <svg
            className="size-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
      )}
    </header>
  );
}
export default SiteHeader;
