"use client";

import React, { useState, useEffect, useCallback } from "react";
import { UserPlus, Mail, ChevronDown, Check, X, Edit2 } from "lucide-react";
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

interface User {
  id: string;
  email: string;
  role: "Admin" | "Reviewer";
  organization: string | null;
  display_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  invited_at: string | null;
  first_login_at: string | null;
  last_login_at: string | null;
}

function formatDate(isoString: string | null): string {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "numeric",
    day: "numeric",
    year: "2-digit",
  });
}

function getInitials(name: string | null, email: string): string {
  if (name) {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }
  return email.slice(0, 2).toUpperCase();
}

function getAvatarColor(email: string): string {
  const colors = [
    "bg-sky-500",
    "bg-emerald-500",
    "bg-violet-500",
    "bg-amber-500",
    "bg-rose-500",
    "bg-cyan-500",
  ];
  const hash = email
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Filters
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<"Admin" | "Reviewer">(
    "Reviewer",
  );
  const [inviteOrg, setInviteOrg] = useState("");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState("");

  // Edit role state
  const [editRole, setEditRole] = useState<"Admin" | "Reviewer">("Reviewer");
  const [editLoading, setEditLoading] = useState(false);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<User[]>("/users");
      setUsers(res.data);
    } catch (err) {
      console.error("Failed to fetch users:", err);
      setUsers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteLoading(true);
    setInviteError("");

    try {
      await apiClient.post("/users/invite", {
        email: inviteEmail,
        role: inviteRole,
        organization: inviteOrg || null,
      });
      setShowInviteModal(false);
      setInviteEmail("");
      setInviteRole("Reviewer");
      setInviteOrg("");
      fetchUsers();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setInviteError(error.response?.data?.detail || "Failed to invite user");
    } finally {
      setInviteLoading(false);
    }
  };

  const handleUpdateRole = async () => {
    if (!editingUser) return;
    setEditLoading(true);

    try {
      await apiClient.put(`/users/${editingUser.id}`, {
        role: editRole,
      });
      setEditingUser(null);
      fetchUsers();
    } catch (err) {
      console.error("Failed to update role:", err);
    } finally {
      setEditLoading(false);
    }
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setEditRole(user.role);
  };

  const handleClear = () => {
    setRoleFilter("");
    setStatusFilter("");
    setCurrentPage(1);
  };

  // Filter users
  const filteredUsers = users.filter((user) => {
    if (roleFilter && user.role !== roleFilter) return false;
    if (statusFilter === "Active" && !user.is_active) return false;
    if (statusFilter === "Inactive" && user.is_active) return false;
    if (statusFilter === "Pending" && user.first_login_at) return false;
    if (statusFilter === "Pending" && !user.invited_at) return false;
    return true;
  });

  const totalPages = Math.ceil(filteredUsers.length / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedUsers = filteredUsers.slice(startIndex, startIndex + pageSize);

  const getStatusLabel = (
    user: User,
  ): { label: string; variant: "success" | "warning" | "danger" } => {
    if (!user.is_active) return { label: "Inactive", variant: "danger" };
    if (!user.first_login_at && user.invited_at)
      return { label: "Pending", variant: "warning" };
    return { label: "Active", variant: "success" };
  };

  return (
    <div className="space-y-6">
      {/* Filtering Row Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Role Filter */}
          <div className="relative">
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">All roles</option>
              <option value="Admin">Admin</option>
              <option value="Reviewer">Reviewer</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">All statuses</option>
              <option value="Active">Active</option>
              <option value="Pending">Pending invite</option>
              <option value="Inactive">Inactive</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Invite button in filter row */}
          <button
            type="button"
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center justify-center space-x-2 px-4 py-2.5 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 transition-colors shadow-sm cursor-pointer"
          >
            <UserPlus className="w-4 h-4" />
            <span>Invite user</span>
          </button>
        </div>

        <button
          type="button"
          onClick={handleClear}
          className="px-6 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-800 rounded-lg text-sm font-medium transition-colors cursor-pointer"
        >
          Clear
        </button>
      </div>

      {/* Main Users Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                User
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Organization
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Role
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Status
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Last login
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider text-right">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100 text-sm text-slate-700">
            {loading ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-8 text-center text-slate-400"
                >
                  Loading users...
                </TableCell>
              </TableRow>
            ) : paginatedUsers.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-8 text-center text-slate-400"
                >
                  No users found.
                </TableCell>
              </TableRow>
            ) : (
              paginatedUsers.map((user) => {
                const status = getStatusLabel(user);
                return (
                  <TableRow
                    key={user.id}
                    className="hover:bg-slate-50/50 transition-colors"
                  >
                    <TableCell className="py-4 px-6">
                      <div className="flex items-center space-x-3">
                        {user.avatar_url ? (
                          <img
                            src={user.avatar_url}
                            alt={user.display_name || user.email}
                            className="w-9 h-9 rounded-full object-cover"
                          />
                        ) : (
                          <div
                            className={`w-9 h-9 rounded-full ${getAvatarColor(user.email)} flex items-center justify-center text-white font-semibold text-xs`}
                          >
                            {getInitials(user.display_name, user.email)}
                          </div>
                        )}
                        <div className="flex flex-col">
                          <span className="font-semibold text-slate-900">
                            {user.display_name || user.email.split("@")[0]}
                          </span>
                          <span className="text-xs text-slate-400">
                            {user.email}
                          </span>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      {user.organization || (
                        <span className="text-slate-400">-</span>
                      )}
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <Badge
                        variant={user.role === "Admin" ? "primary" : "neutral"}
                      >
                        {user.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <Badge variant={status.variant}>{status.label}</Badge>
                    </TableCell>
                    <TableCell className="py-4 px-6 text-slate-600">
                      {formatDate(user.last_login_at)}
                    </TableCell>
                    <TableCell className="py-4 px-6 text-right">
                      <button
                        type="button"
                        onClick={() => openEditModal(user)}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>

        {/* Pagination Controls */}
        {filteredUsers.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing{" "}
              <span className="font-semibold text-slate-700">
                {startIndex + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-700">
                {Math.min(startIndex + pageSize, filteredUsers.length)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-700">
                {filteredUsers.length}
              </span>{" "}
              users
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

      {/* Invite User Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Invite new user
              </h2>
              <button
                type="button"
                onClick={() => setShowInviteModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleInvite} className="p-6 space-y-4">
              {inviteError && (
                <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg">
                  {inviteError}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Email address
                </label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                  placeholder="user@example.com"
                  className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Role
                </label>
                <div className="relative">
                  <select
                    value={inviteRole}
                    onChange={(e) =>
                      setInviteRole(e.target.value as "Admin" | "Reviewer")
                    }
                    className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
                  >
                    <option value="Reviewer">Reviewer</option>
                    <option value="Admin">Admin</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
                <p className="mt-1.5 text-xs text-slate-500">
                  Reviewers can approve/reject submissions. Admins can also
                  manage users and sites.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Organization{" "}
                  <span className="text-slate-400">(optional)</span>
                </label>
                <input
                  type="text"
                  value={inviteOrg}
                  onChange={(e) => setInviteOrg(e.target.value)}
                  placeholder="e.g., Nile Basin Discourse"
                  className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviteLoading}
                  className="inline-flex items-center space-x-2 px-5 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  {inviteLoading ? (
                    <span>Sending...</span>
                  ) : (
                    <>
                      <Mail className="w-4 h-4" />
                      <span>Send invite</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Role Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900">
                Edit user role
              </h2>
              <button
                type="button"
                onClick={() => setEditingUser(null)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center space-x-3">
                {editingUser.avatar_url ? (
                  <img
                    src={editingUser.avatar_url}
                    alt={editingUser.display_name || editingUser.email}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                ) : (
                  <div
                    className={`w-10 h-10 rounded-full ${getAvatarColor(editingUser.email)} flex items-center justify-center text-white font-semibold text-sm`}
                  >
                    {getInitials(editingUser.display_name, editingUser.email)}
                  </div>
                )}
                <div>
                  <p className="font-medium text-slate-900">
                    {editingUser.display_name ||
                      editingUser.email.split("@")[0]}
                  </p>
                  <p className="text-sm text-slate-500">{editingUser.email}</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Role
                </label>
                <div className="relative">
                  <select
                    value={editRole}
                    onChange={(e) =>
                      setEditRole(e.target.value as "Admin" | "Reviewer")
                    }
                    className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
                  >
                    <option value="Reviewer">Reviewer</option>
                    <option value="Admin">Admin</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleUpdateRole}
                  disabled={editLoading || editRole === editingUser.role}
                  className="inline-flex items-center space-x-2 px-5 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  {editLoading ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Save changes</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
