'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Settings, Bell, ChevronDown, LogOut, User } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export default function Header() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Active state logic for main top nav
  const isAdminViewActive = pathname.startsWith('/admin');

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setDropdownOpen(false);
    await logout();
  };

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
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen(!dropdownOpen)}
            className="flex items-center space-x-2 px-3 py-1.5 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt=""
                className="w-6 h-6 rounded-full"
              />
            ) : (
              <User className="w-4 h-4 text-slate-500" />
            )}
            <span className="max-w-[120px] truncate">
              {user?.display_name || user?.email?.split('@')[0] || 'Account'}
            </span>
            <ChevronDown className="w-4 h-4 text-slate-500" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-slate-200 shadow-lg py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              {user && (
                <div className="px-4 py-2 border-b border-slate-100">
                  <div className="text-sm font-medium text-slate-900 truncate">
                    {user.display_name || user.email}
                  </div>
                  <div className="text-xs text-slate-500 truncate">{user.email}</div>
                  <div className="mt-1">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-sky-50 text-sky-700">
                      {user.role}
                    </span>
                  </div>
                </div>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors flex items-center space-x-2"
              >
                <LogOut className="w-4 h-4 text-slate-400" />
                <span>Sign out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
