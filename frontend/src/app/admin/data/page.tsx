"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { ChevronDown } from "lucide-react";
import { adminApiClient } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

interface Submission {
  id: string;
  rawId: string;
  formType: string;
  basinSite: string;
  date: string;
  submittedBy: {
    name: string;
    email: string;
  };
  status: string;
  rawStatus: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  answers: any[];
}

export default function DataOverviewPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [formFilter, setFormFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("Pending");
  const [basinFilter, setBasinFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: "approve" | "reject" | "delete";
    id: string;
  } | null>(null);
  const pageSize = 10;

  useEffect(() => {
    const params: Record<string, string | number> = {};
    if (formFilter) {
      params.form_type = parseInt(formFilter, 10);
    }
    if (statusFilter) {
      params.status = statusFilter.toUpperCase();
    }
    if (basinFilter) {
      params.basin = basinFilter;
    }

    adminApiClient
      .get("/submissions", { params })
      .then((res) => {
        if (res.data) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const fetchedSubmissions = res.data.map((dp: any) => {
            const statusMapped = dp.status
              ? dp.status.charAt(0).toUpperCase() +
                dp.status.slice(1).toLowerCase()
              : "Pending";

            const dateStr = dp.created_at
              ? new Date(dp.created_at).toLocaleDateString("en-US", {
                  month: "numeric",
                  day: "numeric",
                  year: "2-digit",
                })
              : "12.04.80";

            return {
              id: `DP-${dp.id}`,
              rawId: String(dp.id),
              formType: dp.form_name || "Dynamic Ingest",
              basinSite: dp.site_id
                ? `SITE-${String(dp.site_id).slice(0, 8).toUpperCase()}`
                : dp.wetland_id
                  ? `WETLAND-${String(dp.wetland_id).slice(0, 8).toUpperCase()}`
                  : `BASIN-${String(dp.basin_id || "")
                      .slice(0, 8)
                      .toUpperCase()}`,
              date: dateStr,
              submittedBy: {
                name: dp.submitter || "Example Submitter",
                email: "example_email@nbd.org",
              },
              status: statusMapped,
              rawStatus: dp.status || "PENDING",
              answers: dp.answers || [],
            };
          });
          setSubmissions(fetchedSubmissions);
        }
      })
      .catch(() => {
        // Fallback to empty if API fails
      });
  }, [formFilter, statusFilter, basinFilter]);

  const handleApprove = async (id: string) => {
    try {
      const cleanId = id.replace("DP-", "");
      await adminApiClient.patch(`/submissions/${cleanId}/status`, {
        status: "APPROVED",
      });
      setSubmissions((prev) =>
        prev.map((sub) =>
          sub.id === id
            ? { ...sub, status: "Approved", rawStatus: "APPROVED" }
            : sub
        )
      );
    } catch (err) {
      console.error("Failed to approve submission:", err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const cleanId = id.replace("DP-", "");
      await adminApiClient.patch(`/submissions/${cleanId}/status`, {
        status: "REJECTED",
      });
      setSubmissions((prev) =>
        prev.map((sub) =>
          sub.id === id
            ? { ...sub, status: "Rejected", rawStatus: "REJECTED" }
            : sub
        )
      );
    } catch (err) {
      console.error("Failed to reject submission:", err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const cleanId = id.replace("DP-", "");
      await adminApiClient.delete(`/submissions/${cleanId}`);
      setSubmissions((prev) => prev.filter((sub) => sub.id !== id));
      if (expandedRow === id) setExpandedRow(null);
    } catch (err) {
      console.error("Failed to delete submission:", err);
    }
  };

  const handleClear = () => {
    setFormFilter("");
    setStatusFilter("");
    setBasinFilter("");
    setCurrentPage(1);
    setExpandedRow(null);
  };

  const totalPages = Math.ceil(submissions.length / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedSubmissions = submissions.slice(
    startIndex,
    startIndex + pageSize
  );

  return (
    <div className="space-y-6">
      {/* Filtering Row Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Form Filter */}
          <div className="relative">
            <select
              value={formFilter}
              onChange={(e) => {
                setFormFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">Select a form</option>
              <option value="1">Citizen Reporter</option>
              <option value="2">Citizen Scientist</option>
              <option value="3">Indigenous Knowledge</option>
              <option value="4">Lab QA</option>
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
              <option value="">Select status</option>
              <option value="Pending">Pending</option>
              <option value="Approved">Approved</option>
              <option value="Rejected">Rejected</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Basin Filter */}
          <div className="relative">
            <select
              value={basinFilter}
              onChange={(e) => {
                setBasinFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">Select a basin</option>
              <option value="Mara">Mara Basin</option>
              <option value="Sio-Siteko">Sio-Siteko Basin</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
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

      {/* Main Submissions Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Id
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Form
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Basin/Site
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Date
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Submitted by
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Status
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider text-right">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100 text-sm text-slate-700">
            {paginatedSubmissions.map((sub) => {
              const isApprovedOrRejected =
                sub.rawStatus === "APPROVED" || sub.rawStatus === "REJECTED";

              return (
                <React.Fragment key={sub.id}>
                  <TableRow
                    className="hover:bg-slate-50/50 transition-colors cursor-pointer"
                    onClick={() =>
                      setExpandedRow(expandedRow === sub.id ? null : sub.id)
                    }
                  >
                    <TableCell className="py-4 px-6 font-medium text-slate-900">
                      {sub.id}
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                        {sub.formType}
                      </span>
                    </TableCell>
                    <TableCell className="py-4 px-6">{sub.basinSite}</TableCell>
                    <TableCell className="py-4 px-6 font-semibold text-slate-900">
                      {sub.date}
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <div className="flex flex-col">
                        <span className="font-semibold text-slate-900">
                          {sub.submittedBy.name}
                        </span>
                        <span className="text-xs text-slate-400 mt-0.5">
                          {sub.submittedBy.email}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="py-4 px-6">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                          sub.status === "Active" || sub.status === "Approved"
                            ? "bg-green-50 text-green-700 border-green-100"
                            : sub.status === "Pending"
                              ? "bg-orange-50 text-orange-700 border-orange-100"
                              : "bg-red-50 text-red-700 border-red-100"
                        }`}
                      >
                        {sub.status}
                      </span>
                    </TableCell>
                    <TableCell className="py-4 px-6 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <button
                          type="button"
                          disabled={isApprovedOrRejected}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmAction({ type: "reject", id: sub.id });
                          }}
                          className="px-3.5 py-1.5 border border-sky-400 hover:bg-sky-50 text-sky-500 rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
                        >
                          Reject
                        </button>
                        <button
                          type="button"
                          disabled={isApprovedOrRejected}
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmAction({ type: "approve", id: sub.id });
                          }}
                          className="px-3.5 py-1.5 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer disabled:opacity-50 disabled:pointer-events-none"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmAction({ type: "delete", id: sub.id });
                          }}
                          className="px-3.5 py-1.5 bg-red-500 hover:bg-red-600 text-white rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer"
                        >
                          Delete
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                  {expandedRow === sub.id && (
                    <TableRow className="bg-slate-50/30 hover:bg-slate-50/30">
                      <TableCell colSpan={7} className="p-6">
                        <div className="space-y-4 text-left">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="text-sm font-bold text-slate-800">
                                Submission Details
                              </h4>
                              <p className="text-xs text-slate-500 mt-1">
                                Submitter: {sub.submittedBy.name} (
                                {sub.submittedBy.email})
                              </p>
                            </div>
                            <a
                              href={`/admin/data/edit/${sub.rawId}`}
                              className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-bold transition-all shadow-sm cursor-pointer"
                            >
                              Edit Answers
                            </a>
                          </div>
                          <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="bg-slate-50 border-b border-slate-200">
                                  <th className="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide w-2/5">
                                    Question
                                  </th>
                                  <th className="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                                    Answer
                                  </th>
                                </tr>
                              </thead>
                              <tbody>
                                {sub.answers.map((ans) => (
                                  <tr
                                    key={ans.id}
                                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50/50 transition-colors"
                                  >
                                    <td className="px-4 py-2.5 text-xs font-medium text-slate-500 align-top">
                                      {ans.question_label}
                                    </td>
                                    <td className="px-4 py-2.5 align-top">
                                      {ans.read_url ? (
                                        <div className="flex items-center space-x-2">
                                          <Image
                                            src={ans.read_url}
                                            alt={
                                              ans.question_name ||
                                              ans.name ||
                                              "photo"
                                            }
                                            width={48}
                                            height={48}
                                            unoptimized
                                            className="object-cover rounded border border-slate-100 shadow-sm"
                                          />
                                          <a
                                            href={ans.read_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="text-xs text-sky-500 font-bold underline"
                                          >
                                            Open image
                                          </a>
                                        </div>
                                      ) : (
                                        <span className="text-sm font-semibold text-slate-800">
                                          {ans.value !== null &&
                                          ans.value !== undefined &&
                                          ans.value !== ""
                                            ? String(ans.value)
                                            : "—"}
                                        </span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                                {sub.answers.length === 0 && (
                                  <tr>
                                    <td
                                      colSpan={2}
                                      className="px-4 py-4 text-center text-xs text-slate-400"
                                    >
                                      No answers recorded.
                                    </td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
            {paginatedSubmissions.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-8 text-center text-slate-400"
                >
                  No submissions found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination Controls */}
        {submissions.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing{" "}
              <span className="font-semibold text-slate-700">
                {startIndex + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-700">
                {Math.min(startIndex + pageSize, submissions.length)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-700">
                {submissions.length}
              </span>{" "}
              submissions
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

      {confirmAction && (
        <div className="fixed inset-0 bg-slate-950/40 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
          <div className="bg-white rounded-xl p-6 shadow-xl border border-slate-100 max-w-sm w-full space-y-4 animate-scale-up">
            <h3 className="text-sm font-bold text-slate-900 capitalize">
              Confirm {confirmAction.type} Action
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Are you sure you want to {confirmAction.type} submission{" "}
              <span className="font-semibold text-slate-700">
                {confirmAction.id}
              </span>
              ?
              {confirmAction.type === "delete"
                ? " This action cannot be undone."
                : ""}
            </p>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  const { type, id } = confirmAction;
                  setConfirmAction(null);
                  if (type === "approve") await handleApprove(id);
                  else if (type === "reject") await handleReject(id);
                  else if (type === "delete") await handleDelete(id);
                }}
                className={`px-4 py-2 text-white rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  confirmAction.type === "delete"
                    ? "bg-red-500 hover:bg-red-600 shadow-red-100"
                    : "bg-sky-500 hover:bg-sky-600 shadow-sky-100"
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
