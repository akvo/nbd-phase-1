"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Edit2, Trash2, X, AlertTriangle } from "lucide-react";
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

interface Form {
  id: number;
  name: string;
  type: string | null;
  status: number | null; // 1 = DRAFT, 2 = PUBLISHED
  version: number | null;
  published_at: string | null;
  created_at: string | null;
}

function formatDate(isoString: string | null): string {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function FormManagementPage() {
  const router = useRouter();
  const [forms, setForms] = useState<Form[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleteModal, setDeleteModal] = useState<Form | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);

  const fetchForms = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<Form[]>("/forms");
      setForms(res.data);
    } catch (err) {
      console.error("Failed to fetch forms:", err);
      setForms([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchForms();
  }, [fetchForms]);

  const handleDeleteClick = (form: Form) => {
    setDeleteModal(form);
    setDeleteConfirmText("");
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal || deleteConfirmText !== "DELETE") return;

    setDeleteLoading(true);
    try {
      await apiClient.delete(`/forms/${deleteModal.id}`);
      setForms((prev) => prev.filter((f) => f.id !== deleteModal.id));
      setDeleteModal(null);
      setDeleteConfirmText("");
    } catch (err) {
      console.error("Failed to delete form:", err);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleCloseDeleteModal = () => {
    setDeleteModal(null);
    setDeleteConfirmText("");
  };

  const getStatusBadge = (status: number | null) => {
    if (status === 2) {
      return <Badge variant="success">Published</Badge>;
    } else if (status === 1) {
      return <Badge variant="warning">Draft</Badge>;
    }
    return <Badge variant="neutral">-</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Main Forms Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                ID
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Name
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Type
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Status
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Version
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Published
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
                  colSpan={7}
                  className="py-8 text-center text-slate-400"
                >
                  Loading forms...
                </TableCell>
              </TableRow>
            ) : forms.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-8 text-center text-slate-400"
                >
                  No forms found.
                </TableCell>
              </TableRow>
            ) : (
              forms.map((form) => (
                <TableRow
                  key={form.id}
                  className="hover:bg-slate-50/50 transition-colors"
                >
                  <TableCell className="py-4 px-6 font-mono text-slate-500">
                    {form.id}
                  </TableCell>
                  <TableCell className="py-4 px-6 font-semibold text-slate-900">
                    {form.name}
                  </TableCell>
                  <TableCell className="py-4 px-6">
                    {form.type ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
                        {form.type}
                      </span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="py-4 px-6">
                    {getStatusBadge(form.status)}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-slate-600">
                    {form.version ? `v${form.version}` : "-"}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-slate-600">
                    {formatDate(form.published_at)}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        type="button"
                        onClick={() =>
                          router.push(`/admin/sites/forms/${form.id}`)
                        }
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteClick(form)}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-red-200 hover:bg-red-50 text-red-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Delete</span>
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                <h2 className="text-lg font-semibold">Delete Form</h2>
              </div>
              <button
                type="button"
                onClick={handleCloseDeleteModal}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-red-50 border border-red-100 rounded-lg p-4">
                <p className="text-sm text-red-800">
                  You are about to delete{" "}
                  <span className="font-semibold">{deleteModal.name}</span>.
                  This action cannot be undone and will permanently remove the
                  form and all associated data.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Type{" "}
                  <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-red-600">
                    DELETE
                  </span>{" "}
                  to confirm
                </label>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder="DELETE"
                  className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 transition-all"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={handleCloseDeleteModal}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeleteConfirm}
                  disabled={deleteConfirmText !== "DELETE" || deleteLoading}
                  className="inline-flex items-center space-x-2 px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  {deleteLoading ? (
                    <span>Deleting...</span>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      <span>Delete Form</span>
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
