'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import Header from '@/components/admin/header';
import Tabs from '@/components/admin/tabs';
import { Download, Plus } from 'lucide-react';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Dynamic Page Title & Subtitle based on the active tab/route
  let title = 'Admin Dashboard';
  let subtitle = 'Nile Basin Discourse platform administrative workspace';
  let showBadge = false;
  let badgeLabel = '240 instances';
  let isTabbedRoute = false;

  if (pathname === '/admin/data') {
    title = 'Data overview';
    subtitle = 'Search and filter across all submitted data • Click a row to review';
    showBadge = true;
    isTabbedRoute = true;
  } else if (pathname === '/admin/users') {
    title = 'User administration';
    subtitle = 'Manage staff members, roles, and OIDC sign-in invitations';
    isTabbedRoute = true;
  } else if (pathname === '/admin/sites') {
    title = 'Site configuration';
    subtitle = 'Manage basin details, sub-county bounds, and fixed monitoring points';
    isTabbedRoute = true;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col font-sans">
      {/* Top Global Navigation Bar */}
      <Header />

      {/* Main Administrative Container */}
      <div className="flex-1 max-w-7xl w-full mx-auto px-8 py-8 space-y-6">

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

          {/* Action buttons (CSV Download & Add new) - Only on tabbed data pages */}
          {isTabbedRoute && (
            <div className="flex items-center space-x-3">
              <button
                type="button"
                className="inline-flex items-center space-x-2 px-4 py-2 border border-slate-200 bg-white rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
              >
                <Download className="w-4 h-4 text-slate-500" />
                <span>Download CSV</span>
              </button>
              <button
                type="button"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                <span>Add new</span>
              </button>
            </div>
          )}
        </div>

        {/* Sub-Navigation Section Tabs - Only shown on tabbed routes */}
        {isTabbedRoute && <Tabs />}

        {/* Dynamic Nested Sub-view Viewport */}
        <main className="w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
