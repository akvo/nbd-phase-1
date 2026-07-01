"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Edit2,
  Trash2,
  AlertTriangle,
  Loader2,
  Globe,
  Download,
  FileJson,
  ChevronDown,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

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
  const [loadingEditId, setLoadingEditId] = useState<number | null>(null);
  const [loadingPublishId, setLoadingPublishId] = useState<number | null>(null);
  const [publishModal, setPublishModal] = useState<Form | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [downloadingCascade, setDownloadingCascade] = useState(false);

  const handleDownload = async (
    url: string,
    filename: string,
    formId?: number
  ) => {
    if (formId) {
      setDownloadingId(formId);
    } else {
      setDownloadingCascade(true);
    }
    try {
      const response = await apiClient.get(url, { responseType: "blob" });
      const contentType =
        (response.headers["content-type"] as string) ||
        "application/octet-stream";
      const blob = new Blob([response.data], { type: contentType });
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("Failed to download file:", err);
    } finally {
      setDownloadingId(null);
      setDownloadingCascade(false);
    }
  };

  const handleEditClick = (formId: number) => {
    setLoadingEditId(formId);
    setTimeout(() => {
      router.push(`/admin/resources/forms/${formId}`);
    }, 10);
  };

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
    if (typeof window !== "undefined") {
      fetchForms();
    }
  }, [fetchForms]);

  const handlePublishClick = (form: Form) => {
    setPublishModal(form);
  };

  const handlePublishConfirm = async () => {
    if (!publishModal) return;
    setLoadingPublishId(publishModal.id);
    try {
      await apiClient.post(`/forms/${publishModal.id}/publish`);
      setPublishModal(null);
      await fetchForms();
    } catch (err) {
      console.error("Failed to publish form:", err);
    } finally {
      setLoadingPublishId(null);
    }
  };

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
      <div className="flex justify-between items-center bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Form Management</h1>
          <p className="text-sm text-slate-500">
            Manage and export your form configurations and geographic datasets.
          </p>
        </div>
        <Button
          variant="outline"
          disabled={downloadingCascade}
          onClick={() =>
            handleDownload(
              "/reference/spatial-cascade/csv",
              "spatial_cascade.csv"
            )
          }
          className="text-xs font-semibold cursor-pointer inline-flex items-center space-x-2"
        >
          {downloadingCascade ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Download className="w-3.5 h-3.5" />
          )}
          <span>Download Spatial Cascade CSV</span>
        </Button>
      </div>

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
              forms.map((form, index) => {
                const isLastRow = index === forms.length - 1;
                const openUpward = isLastRow && forms.length > 2;

                return (
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
                          onClick={() => handleEditClick(form.id)}
                          disabled={loadingEditId !== null}
                          className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                        >
                          {loadingEditId === form.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Edit2 className="w-3.5 h-3.5" />
                          )}
                          <span>
                            {loadingEditId === form.id ? "Loading..." : "Edit"}
                          </span>
                        </button>
                        {form.status === 1 && (
                          <button
                            type="button"
                            onClick={() => handlePublishClick(form)}
                            disabled={
                              loadingPublishId !== null ||
                              loadingEditId !== null
                            }
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-sky-200 hover:bg-sky-50 text-sky-700 rounded-lg text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                          >
                            {loadingPublishId === form.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Globe className="w-3.5 h-3.5" />
                            )}
                            <span>
                              {loadingPublishId === form.id
                                ? "Publishing..."
                                : "Publish"}
                            </span>
                          </button>
                        )}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button
                              type="button"
                              disabled={downloadingId !== null}
                              className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                            >
                              {downloadingId === form.id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Download className="w-3.5 h-3.5" />
                              )}
                              <span>Export</span>
                              <ChevronDown className="w-3.5 h-3.5" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent
                            align="right"
                            side={openUpward ? "top" : "bottom"}
                          >
                            <DropdownMenuItem
                              onClick={() =>
                                handleDownload(
                                  `/forms/${form.id}/export/json`,
                                  `${form.name.toLowerCase().replace(/\s+/g, "_")}_published.json`,
                                  form.id
                                )
                              }
                              disabled={
                                downloadingId !== null || !form.published_at
                              }
                            >
                              <FileJson className="w-3.5 h-3.5 mr-2 text-slate-500" />
                              <span>JSON (Published)</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                handleDownload(
                                  `/forms/${form.id}/export/json?draft=true`,
                                  `${form.name.toLowerCase().replace(/\s+/g, "_")}_draft.json`,
                                  form.id
                                )
                              }
                              disabled={downloadingId !== null}
                            >
                              <FileJson className="w-3.5 h-3.5 mr-2 text-slate-400" />
                              <span>JSON (Draft)</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                handleDownload(
                                  `/forms/${form.id}/export/xlsform`,
                                  `${form.name.toLowerCase().replace(/\s+/g, "_")}_published_xlsform.xlsx`,
                                  form.id
                                )
                              }
                              disabled={
                                downloadingId !== null || !form.published_at
                              }
                            >
                              <Download className="w-3.5 h-3.5 mr-2 text-slate-500" />
                              <span>XLSForm (Published)</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() =>
                                handleDownload(
                                  `/forms/${form.id}/export/xlsform?draft=true`,
                                  `${form.name.toLowerCase().replace(/\s+/g, "_")}_draft_xlsform.xlsx`,
                                  form.id
                                )
                              }
                              disabled={downloadingId !== null}
                            >
                              <Download className="w-3.5 h-3.5 mr-2 text-slate-400" />
                              <span>XLSForm (Draft)</span>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
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
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <Dialog
        open={!!deleteModal}
        onOpenChange={(open) => !open && handleCloseDeleteModal()}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              <span>Delete Form</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-red-50 border border-red-100 rounded-lg p-4">
              <p className="text-sm text-red-800">
                You are about to delete{" "}
                <span className="font-semibold">{deleteModal?.name}</span>. This
                action cannot be undone and will permanently remove the form and
                all associated data.
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
          </div>
          <DialogFooter className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              type="button"
              onClick={handleCloseDeleteModal}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteConfirmText !== "DELETE" || deleteLoading}
            >
              {deleteLoading ? (
                <span>Deleting...</span>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Form</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={!!publishModal}
        onOpenChange={(open) => !open && setPublishModal(null)}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2 text-sky-600">
              <Globe className="w-5 h-5" />
              <span>Publish Form</span>
            </DialogTitle>
          </DialogHeader>
          <DialogDescription className="text-sky-800 bg-sky-50 border border-sky-100 rounded-lg p-4">
            You are about to publish a new version of{" "}
            <span className="font-semibold">{publishModal?.name}</span>. This
            will freeze the current draft questions and make them live for new
            submissions.
          </DialogDescription>
          <DialogFooter className="flex justify-end gap-2 pt-4">
            <Button
              variant="outline"
              type="button"
              onClick={() => setPublishModal(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="default"
              className="bg-sky-100 hover:bg-sky-200 text-sky-900 font-semibold"
              onClick={handlePublishConfirm}
              disabled={loadingPublishId !== null}
            >
              {loadingPublishId ? (
                <span>Publishing...</span>
              ) : (
                <>
                  <Globe className="w-4 h-4" />
                  <span>Publish Draft</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
