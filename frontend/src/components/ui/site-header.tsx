import React, { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher } from "@/components/ui/language-switcher";
import { apiClient } from "@/lib/api";
import { useTranslations } from "next-intl";
import { useDomainOptional, MonitoringDomain } from "@/context/domain-context";

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

const DOMAINS = [
  { value: "wetland", icon: "🌿", label: "Wetland Monitoring" },
  { value: "pollution", icon: "⚠", label: "Pollution Reports" },
] as const;

export function SiteHeader({ showActions = true }: SiteHeaderProps) {
  const t = useTranslations();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Dashboard nav state
  const [dashMenuOpen, setDashMenuOpen] = useState(false);
  const dashMenuRef = useRef<HTMLDivElement>(null);
  const domainContext = useDomainOptional();

  // Fetch current user for the public page (AuthContext skips non-admin routes)
  useEffect(() => {
    apiClient
      .get<AuthUser>("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => setUser(null))
      .finally(() => setUserLoading(false));
  }, []);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownOpen &&
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false);
      }
      if (
        dashMenuOpen &&
        dashMenuRef.current &&
        !dashMenuRef.current.contains(e.target as Node)
      ) {
        setDashMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownOpen, dashMenuOpen]);

  const handleSignOut = async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // ignore
    }
    setUser(null);
    setDropdownOpen(false);
    window.location.href = "/";
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
      <div className="flex items-center gap-6">
        <div
          className="flex items-center gap-2 md:gap-3 cursor-pointer shrink-0"
          onClick={() => (window.location.href = "/")}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/logo.svg"
            alt={t("header.brand")}
            className="h-9 w-9 md:h-10 md:w-10"
          />
          <div className="flex flex-col">
            <span className="text-sm md:text-base font-bold text-[#4a90c4] leading-tight">
              {t("header.brand")}
            </span>
            <span className="hidden md:inline text-xs text-slate-500 leading-tight">
              {t("header.subtitle")}
            </span>
          </div>
        </div>
      </div>

      {showActions && (
        <>
          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center gap-3">
            {/* Dashboard Navigation flyout — Desktop Only */}
            {domainContext && (
              <div className="relative hidden md:block" ref={dashMenuRef}>
                <button
                  id="site-header-dashboard-menu-btn"
                  onClick={() => setDashMenuOpen((p) => !p)}
                  className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 hover:text-[#4a90c4] transition-colors focus:outline-none"
                >
                  <span>Dashboard</span>
                  <span className="text-xs text-slate-400 font-normal">
                    (
                    {domainContext.selectedDomain === "wetland"
                      ? "🌿 Wetland"
                      : "⚠ Pollution"}
                    )
                  </span>
                  <svg
                    className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-150 ${dashMenuOpen ? "rotate-180" : ""}`}
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

                {dashMenuOpen && (
                  <div
                    id="site-header-dashboard-submenu"
                    className="absolute left-0 top-full mt-2 w-52 bg-white rounded-xl border border-slate-200 shadow-xl py-1.5 z-50 animate-fade-in"
                    role="menu"
                  >
                    {DOMAINS.map((d) => (
                      <button
                        key={d.value}
                        role="menuitem"
                        onClick={() => {
                          domainContext.setSelectedDomain(d.value);
                          setDashMenuOpen(false);
                        }}
                        className="w-full flex items-center justify-between px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
                      >
                        <span className="flex items-center gap-2">
                          <span>{d.icon}</span>
                          <span>{d.label}</span>
                        </span>
                        {domainContext.selectedDomain === d.value && (
                          <span className="text-xs font-bold text-[#4a90c4]">
                            ✓
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
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
                variant="outline"
                onClick={() => (window.location.href = "/login")}
              >
                {t("common.login")}
              </Button>
            )}
          </div>

          {/* Mobile Hamburger Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsMenuOpen((p) => !p)}
              className="bg-white hover:bg-slate-100 p-2 rounded-lg text-slate-700 transition-colors outline-none"
              aria-label="Toggle menu"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                {isMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>

          {/* Mobile Right Drawer Overlay Menu */}
          {isMenuOpen && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 animate-fade-in"
                onClick={() => setIsMenuOpen(false)}
              />
              {/* Right Drawer Sheet */}
              <div className="fixed inset-y-0 right-0 w-72 max-w-[80vw] bg-white shadow-2xl z-50 p-5 flex flex-col gap-5 animate-slide-in">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <img
                      src="/logo.svg"
                      alt={t("header.brand")}
                      className="h-8 w-8"
                    />
                    <span className="text-sm font-bold text-[#4a90c4]">
                      {t("header.brand")}
                    </span>
                  </div>
                  <button
                    onClick={() => setIsMenuOpen(false)}
                    className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>

                {domainContext && (
                  <div className="flex flex-col gap-1.5 w-full">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Dashboard Views
                    </span>
                    <div className="relative w-full">
                      <select
                        value={domainContext.selectedDomain}
                        onChange={(e) => {
                          domainContext.setSelectedDomain(
                            e.target.value as MonitoringDomain
                          );
                          setIsMenuOpen(false);
                        }}
                        className="h-10 w-full rounded-lg border border-grey-300 bg-white px-3.5 py-2 text-sm text-nbd-text-dark transition-colors outline-none focus-visible:border-[#4a90c4] focus-visible:ring-2 focus-visible:ring-[#4a90c4]/20 appearance-none"
                      >
                        {DOMAINS.map((d) => (
                          <option key={d.value} value={d.value}>
                            {d.icon} {d.label}
                          </option>
                        ))}
                      </select>
                      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3.5 text-nbd-text-dark">
                        <svg
                          className="size-4 fill-none stroke-current"
                          viewBox="0 0 24 24"
                        >
                          <polyline
                            points="6 9 12 15 18 9"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                )}

                <hr className="border-slate-100" />

                <div className="flex items-center justify-between py-1">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                    Language
                  </span>
                  <LanguageSwitcher />
                </div>

                <hr className="border-slate-100" />

                {userLoading ? null : user ? (
                  <div className="flex flex-col gap-3 mt-auto">
                    <div className="flex items-center gap-3 p-1">
                      <span className="w-8 h-8 rounded-full bg-nbd-primary flex items-center justify-center text-white text-xs font-bold">
                        {initials}
                      </span>
                      <div className="flex flex-col min-w-0">
                        <span className="text-xs font-semibold text-slate-800 truncate">
                          {user.display_name ?? user.email}
                        </span>
                        <span className="text-[10px] text-slate-400 truncate">
                          {user.email}
                        </span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      {user.role === "Admin" && (
                        <a
                          href="/admin"
                          className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                        >
                          Admin Panel
                        </a>
                      )}
                      <button
                        onClick={handleSignOut}
                        className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-red-100 text-xs font-semibold text-red-500 hover:bg-red-50 transition-colors w-full"
                      >
                        Sign Out
                      </button>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    onClick={() => (window.location.href = "/login")}
                    className="w-full justify-center mt-auto"
                  >
                    {t("common.login")}
                  </Button>
                )}
              </div>
            </>
          )}
        </>
      )}
    </header>
  );
}
export default SiteHeader;
