"use client";

import React, { useState, useEffect, useCallback } from "react";
import { ChevronDown } from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface AuditLog {
  id: string;
  actor_id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
}

interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  page: number;
  page_size: number;
}

interface User {
  id: string;
  email: string;
  display_name: string | null;
}

const ACTION_OPTIONS = [
  { value: "", label: "All actions" },
  { value: "APPROVE", label: "Approve" },
  { value: "REJECT", label: "Reject" },
  { value: "EDIT", label: "Edit" },
  { value: "DELETE", label: "Delete" },
  { value: "INVITE_USER", label: "Invite User" },
  { value: "UPDATE_ROLE", label: "Update Role" },
  { value: "ALERT", label: "Alert" },
];

const ENTITY_TYPE_OPTIONS = [
  { value: "", label: "All types" },
  { value: "user", label: "User" },
  { value: "submission", label: "Submission" },
  { value: "site", label: "Site" },
  { value: "form", label: "Form" },
  { value: "ussd_webhook", label: "USSD" },
  { value: "whatsapp_webhook", label: "WhatsApp" },
];

function formatEntityType(entityType: string): string {
  const mapping: Record<string, string> = {
    ussd_webhook: "USSD",
    whatsapp_webhook: "WhatsApp",
    user: "User",
    submission: "Submission",
    site: "Site",
    form: "Form",
  };
  return mapping[entityType] || entityType;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getActionBadgeVariant(
  action: string
): "primary" | "success" | "warning" | "danger" | "neutral" {
  switch (action) {
    case "APPROVE":
    case "INVITE_USER":
      return "success";
    case "REJECT":
    case "DELETE":
      return "danger";
    case "EDIT":
    case "UPDATE_ROLE":
      return "warning";
    case "ALERT":
      return "primary";
    default:
      return "neutral";
  }
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [users, setUsers] = useState<Record<string, User>>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [actionFilter, setActionFilter] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", String(currentPage));
      params.append("page_size", String(pageSize));

      if (actionFilter) params.append("action", actionFilter);
      if (entityTypeFilter) params.append("entity_type", entityTypeFilter);
      if (dateFrom)
        params.append("date_from", new Date(dateFrom).toISOString());
      if (dateTo) {
        // Set end of day for date_to
        const endDate = new Date(dateTo);
        endDate.setHours(23, 59, 59, 999);
        params.append("date_to", endDate.toISOString());
      }

      const res = await apiClient.get<AuditLogListResponse>(
        `/audit-logs?${params.toString()}`
      );
      setLogs(res.data.items);
      setTotal(res.data.total);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
      setLogs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, actionFilter, entityTypeFilter, dateFrom, dateTo]);

  // Fetch users for actor name resolution
  useEffect(() => {
    apiClient
      .get<User[]>("/users")
      .then((res) => {
        const userMap: Record<string, User> = {};
        res.data.forEach((user) => {
          userMap[user.id] = user;
        });
        setUsers(userMap);
      })
      .catch(() => {
        // Users endpoint might fail for non-admins, but we're on admin-only page
      });
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const handleClear = () => {
    setActionFilter("");
    setEntityTypeFilter("");
    setDateFrom("");
    setDateTo("");
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;

  const getActorDisplay = (
    actorId: string
  ): { name: string; email: string } => {
    const user = users[actorId];
    if (user) {
      return {
        name: user.display_name || user.email.split("@")[0],
        email: user.email,
      };
    }
    return {
      name: "Unknown",
      email: actorId.slice(0, 8) + "...",
    };
  };

  return (
    <div className="space-y-6">
      {/* Filtering Row Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-end justify-between gap-4 shadow-sm">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Action Filter */}
          <div className="relative">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Action
            </label>
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 bottom-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Entity Type Filter */}
          <div className="relative">
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              Entity type
            </label>
            <select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              {ENTITY_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 bottom-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Date From */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              From date
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
            />
          </div>

          {/* Date To */}
          <div>
            <label className="block text-xs font-medium text-slate-500 mb-1.5">
              To date
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-white border border-slate-200 rounded-lg px-4 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleClear}
          className="px-6 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
        >
          Clear
        </button>
      </div>

      {/* Main Audit Logs Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Timestamp
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Actor
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Action
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Entity type
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Entity ID
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100 text-sm text-slate-700">
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-8 text-center text-slate-400"
                >
                  Loading...
                </TableCell>
              </TableRow>
            ) : logs.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-8 text-center text-slate-400"
                >
                  No audit logs found.
                </TableCell>
              </TableRow>
            ) : (
              logs.map((log) => {
                const actor = getActorDisplay(log.actor_id);
                return (
                  <TableRow
                    key={log.id}
                    className="hover:bg-slate-50/50 transition-colors"
                  >
                    <TableCell className="py-4 px-6 font-medium text-slate-900">
                      {formatTimestamp(log.timestamp)}
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <div className="flex flex-col">
                        <span className="font-semibold text-slate-900">
                          {actor.name}
                        </span>
                        <span className="text-xs text-slate-400 mt-0.5">
                          {actor.email}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <Badge variant={getActionBadgeVariant(log.action)}>
                        {log.action.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      {formatEntityType(log.entity_type)}
                    </TableCell>
                    <TableCell className="py-4 px-6 font-mono text-xs text-slate-500">
                      {log.entity_id.length > 20
                        ? `${log.entity_id.slice(0, 8)}...${log.entity_id.slice(-8)}`
                        : log.entity_id}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* Pagination Controls */}
        {total > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing{" "}
              <span className="font-semibold text-slate-700">
                {startIndex + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-700">
                {Math.min(startIndex + pageSize, total)}
              </span>{" "}
              of <span className="font-semibold text-slate-700">{total}</span>{" "}
              entries
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent transition-colors cursor-pointer"
              >
                Previous
              </button>
              <span className="text-xs text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() =>
                  setCurrentPage((p) => Math.min(p + 1, totalPages))
                }
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 border border-slate-200 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent transition-colors cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
