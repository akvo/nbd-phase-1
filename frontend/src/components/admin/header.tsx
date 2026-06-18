'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Settings,
  Bell,
  ChevronDown,
  LogOut,
  User,
  CheckCircle,
  XCircle,
  Pencil,
  Trash2,
  UserPlus,
  AlertTriangle,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/lib/api';

interface AuditLog {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
}

function formatTimeAgo(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function formatAction(action: string): string {
  return action.replace(/_/g, ' ').toLowerCase();
}

function formatEntityType(entityType: string): string {
  const mapping: Record<string, string> = {
    'ussd_webhook': 'USSD',
    'whatsapp_webhook': 'WhatsApp',
    'user': 'user',
    'submission': 'submission',
    'site': 'site',
    'form': 'form',
  };
  return mapping[entityType] || entityType;
}

function getActionIcon(action: string) {
  switch (action) {
    case 'APPROVE':
      return <CheckCircle className="w-4 h-4 text-emerald-500" />;
    case 'REJECT':
      return <XCircle className="w-4 h-4 text-rose-500" />;
    case 'EDIT':
      return <Pencil className="w-4 h-4 text-amber-500" />;
    case 'DELETE':
      return <Trash2 className="w-4 h-4 text-rose-500" />;
    case 'INVITE_USER':
      return <UserPlus className="w-4 h-4 text-sky-500" />;
    case 'ALERT':
      return <AlertTriangle className="w-4 h-4 text-amber-500" />;
    default:
      return <Bell className="w-4 h-4 text-slate-400" />;
  }
}

function getActionColor(action: string): string {
  switch (action) {
    case 'APPROVE':
      return 'bg-emerald-50 text-emerald-700';
    case 'REJECT':
    case 'DELETE':
      return 'bg-rose-50 text-rose-700';
    case 'EDIT':
    case 'ALERT':
      return 'bg-amber-50 text-amber-700';
    case 'INVITE_USER':
      return 'bg-sky-50 text-sky-700';
    default:
      return 'bg-slate-50 text-slate-700';
  }
}

export default function Header() {
  const pathname = usePathname();
  const { user, logout, isAdmin } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [recentLogs, setRecentLogs] = useState<AuditLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  // Active state logic for main top nav
  const isAdminViewActive = pathname.startsWith('/admin');

  // Fetch recent activity logs for admins
  useEffect(() => {
    if (isAdmin) {
      setLogsLoading(true);
      apiClient.get('/audit-logs?page_size=5')
        .then(res => {
          if (res.data?.items) {
            setRecentLogs(res.data.items);
          }
        })
        .catch(() => {
          // Silently fail if not authorized or error
        })
        .finally(() => {
          setLogsLoading(false);
        });
    }
  }, [isAdmin]);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setNotifOpen(false);
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
        <div className="relative" ref={notifRef}>
          <button
            type="button"
            aria-label="Notifications"
            onClick={() => isAdmin && setNotifOpen(!notifOpen)}
            className={`p-2 rounded-full hover:bg-slate-50 hover:text-slate-800 transition-colors relative ${!isAdmin ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <Bell className="w-5 h-5" />
            {isAdmin && recentLogs.length > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full" />
            )}
          </button>

          {notifOpen && isAdmin && (
            <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl border border-slate-200 shadow-xl z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Recent Activity</h3>
                <span className="text-xs text-slate-400">{recentLogs.length} latest</span>
              </div>
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                {logsLoading ? (
                  <div className="px-4 py-8 text-center">
                    <div className="w-6 h-6 border-2 border-slate-200 border-t-sky-500 rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-sm text-slate-400">Loading...</p>
                  </div>
                ) : recentLogs.length === 0 ? (
                  <div className="px-4 py-8 text-center">
                    <Bell className="w-8 h-8 text-slate-200 mx-auto mb-2" />
                    <p className="text-sm text-slate-400">No recent activity</p>
                  </div>
                ) : (
                  recentLogs.map((log) => (
                    <div
                      key={log.id}
                      className="px-4 py-3 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-slate-100">
                          {getActionIcon(log.action)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getActionColor(log.action)}`}>
                              {formatAction(log.action)}
                            </span>
                            <span className="text-xs text-slate-400">
                              {formatTimeAgo(log.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600">
                            {formatEntityType(log.entity_type)}
                            <span className="text-slate-400 ml-1 font-mono text-xs">
                              #{log.entity_id.length > 8 ? log.entity_id.slice(0, 8) : log.entity_id}
                            </span>
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
              <Link
                href="/admin/audit-logs"
                onClick={() => setNotifOpen(false)}
                className="flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-sky-600 hover:text-sky-700 hover:bg-sky-50 border-t border-slate-100 transition-colors"
              >
                <span>View all activity</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>

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
