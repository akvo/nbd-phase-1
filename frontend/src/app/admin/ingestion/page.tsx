"use client";

import React, { useState, useEffect } from "react";
import {
  ChevronDown,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from "lucide-react";
import { adminApiClient } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

interface DeadLetter {
  id: string;
  source_system: string;
  raw_payload: any;
  error_reason: string;
  status: string;
  created_at: string;
}

export default function IngestionPage() {
  const [records, setRecords] = useState<DeadLetter[]>([]);
  const [statusFilter, setStatusFilter] = useState("Pending Triage");
  const [sourceFilter, setSourceFilter] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchRecords = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (statusFilter) {
      params.status = statusFilter;
    }
    if (sourceFilter) {
      params.source_system = sourceFilter;
    }

    adminApiClient
      .get("/dead-letters", { params })
      .then((res) => {
        if (res.data) {
          setRecords(res.data);
        }
      })
      .catch((err) => {
        console.error("Failed to fetch dead letters:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchRecords();
  }, [statusFilter, sourceFilter]);

  const handleAcknowledge = async (id: string) => {
    try {
      await adminApiClient.patch(`/dead-letters/${id}`, {
        status: "Acknowledged",
      });
      // Update local state to reflect acknowledged status or remove if filtering for pending
      if (statusFilter === "Pending Triage") {
        setRecords((prev) => prev.filter((r) => r.id !== id));
      } else {
        setRecords((prev) =>
          prev.map((r) => (r.id === id ? { ...r, status: "Acknowledged" } : r))
        );
      }
    } catch (err) {
      console.error("Failed to acknowledge dead letter:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">
            Data Ingestion & Sync (DLQ)
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Monitor and triage quarantined submissions in the Dead-Letter Queue
          </p>
        </div>
        <button
          type="button"
          onClick={fetchRecords}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-sm transition-colors cursor-pointer disabled:opacity-55"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter row */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-4 shadow-sm">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="Pending Triage">Pending Triage</option>
              <option value="Acknowledged">Acknowledged</option>
              <option value="Resolved">Resolved</option>
              <option value="Discarded">Discarded</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          {/* Source System Filter */}
          <div className="relative">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
            >
              <option value="">All Source Systems</option>
              <option value="KoboToolbox">KoboToolbox</option>
              <option value="USSD">USSD</option>
              <option value="WHATSAPP">WhatsApp</option>
            </select>
            <ChevronDown className="absolute right-3 top-3 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* DLQ Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                ID
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Source System
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Error Reason
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Quarantined At
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
            {records.map((rec) => {
              const formattedDate = rec.created_at
                ? new Date(rec.created_at).toLocaleString()
                : "Unknown";

              return (
                <TableRow
                  key={rec.id}
                  className="hover:bg-slate-50/50 transition-colors"
                >
                  <TableCell className="py-4 px-6 font-mono text-xs text-slate-500">
                    {rec.id.slice(0, 8)}...
                  </TableCell>
                  <TableCell className="py-4 px-6">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 border border-slate-200">
                      {rec.source_system}
                    </span>
                  </TableCell>
                  <TableCell
                    className="py-4 px-6 font-medium text-slate-900 max-w-xs truncate"
                    title={rec.error_reason}
                  >
                    {rec.error_reason}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-slate-500">
                    {formattedDate}
                  </TableCell>
                  <TableCell className="py-4 px-6">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        rec.status === "Pending Triage"
                          ? "bg-amber-50 text-amber-700 border-amber-100"
                          : rec.status === "Acknowledged"
                            ? "bg-blue-50 text-blue-700 border-blue-100"
                            : rec.status === "Resolved"
                              ? "bg-green-50 text-green-700 border-green-100"
                              : "bg-slate-100 text-slate-600 border-slate-200"
                      }`}
                    >
                      {rec.status}
                    </span>
                  </TableCell>
                  <TableCell className="py-4 px-6 text-right">
                    {rec.status === "Pending Triage" && (
                      <button
                        type="button"
                        onClick={() => handleAcknowledge(rec.id)}
                        className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer"
                      >
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>Acknowledge</span>
                      </button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
            {records.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="py-12 text-center text-slate-400"
                >
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <AlertTriangle className="w-8 h-8 text-slate-300" />
                    <span>No quarantined dead-letters found.</span>
                  </div>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
