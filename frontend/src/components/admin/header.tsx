'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Settings, Bell, ChevronDown } from 'lucide-react';

export default function Header() {
  const pathname = usePathname();

  // Active state logic for main top nav
  const isAdminViewActive = pathname.startsWith('/admin');

  return (
    <header className="h-16 border-b border-slate-200 bg-white px-8 flex items-center justify-between w-full">
      {/* Left Navigation Links */}
      <div className="flex items-center space-x-1">
        <Link
          href="/admin"
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            isAdminViewActive
              ? 'bg-sky-50 text-sky-500'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          Admin view
        </Link>
        <Link
          href="/admin/projects-placeholder"
          className="px-4 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
        >
          Projects
        </Link>
        <Link
          href="/admin/tasks-placeholder"
          className="px-4 py-1.5 rounded-lg text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-colors"
        >
          Tasks
        </Link>
      </div>

      {/* Right User Utility Actions */}
      <div className="flex items-center space-x-4 text-slate-500">
        <button
          type="button"
          aria-label="Settings"
          className="p-2 rounded-full hover:bg-slate-50 hover:text-slate-800 transition-colors"
        >
          <Settings className="w-5 h-5" />
        </button>
        <button
          type="button"
          aria-label="Notifications"
          className="p-2 rounded-full hover:bg-slate-50 hover:text-slate-800 transition-colors relative"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full" />
        </button>
        
        {/* Account Dropdown */}
        <div className="relative">
          <button
            type="button"
            className="flex items-center space-x-2 px-3 py-1.5 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span>Account</span>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>
        </div>
      </div>
    </header>
  );
}
