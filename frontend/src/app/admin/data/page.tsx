'use client';

import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';

interface Submission {
  id: string;
  formType: string;
  basinSite: string;
  date: string;
  submittedBy: {
    name: string;
    email: string;
  };
  status: string;
}

export default function DataOverviewPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [formFilter, setFormFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [basinFilter, setBasinFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    apiClient.get('/submissions')
      .then(res => {
        if (res.data) {
          const fetchedSubmissions = res.data.map((dp: any) => {
            const statusMapped = dp.status
              ? dp.status.charAt(0).toUpperCase() + dp.status.slice(1).toLowerCase()
              : 'Pending';

            const dateStr = dp.created_at
              ? new Date(dp.created_at).toLocaleDateString('en-US', {
                  month: 'numeric',
                  day: 'numeric',
                  year: '2-digit'
                })
              : '12.04.80';

            return {
              id: `DP-${dp.id}`,
              formType: dp.form_name || 'Dynamic Ingest',
              basinSite: dp.site_id
                ? `SITE-${String(dp.site_id).slice(0, 8).toUpperCase()}`
                : dp.wetland_id
                ? `WETLAND-${String(dp.wetland_id).slice(0, 8).toUpperCase()}`
                : `BASIN-${String(dp.basin_id || '').slice(0, 8).toUpperCase()}`,
              date: dateStr,
              submittedBy: {
                name: dp.submitter || 'Example Submitter',
                email: 'example_email@nbd.org'
              },
              status: statusMapped
            };
          });
          setSubmissions(fetchedSubmissions);
        }
      })
      .catch(() => {
        // Fallback to empty if API fails
      });
  }, []);

  const handleApprove = async (id: string) => {
    try {
      const cleanId = id.replace('DP-', '');
      await apiClient.patch(`/submissions/${cleanId}/status`, { status: 'APPROVED' });
      setSubmissions(prev =>
        prev.map(sub => (sub.id === id ? { ...sub, status: 'Approved' } : sub))
      );
    } catch (err) {
      console.error("Failed to approve submission:", err);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const cleanId = id.replace('DP-', '');
      await apiClient.patch(`/submissions/${cleanId}/status`, { status: 'REJECTED' });
      setSubmissions(prev =>
        prev.map(sub => (sub.id === id ? { ...sub, status: 'Rejected' } : sub))
      );
    } catch (err) {
      console.error("Failed to reject submission:", err);
    }
  };


  const handleClear = () => {
    setFormFilter('');
    setStatusFilter('');
    setBasinFilter('');
    setCurrentPage(1);
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (formFilter && sub.formType !== formFilter) return false;
    if (statusFilter && sub.status !== statusFilter) return false;
    if (basinFilter && !sub.basinSite.includes(basinFilter)) return false;
    return true;
  });

  const totalPages = Math.ceil(filteredSubmissions.length / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedSubmissions = filteredSubmissions.slice(startIndex, startIndex + pageSize);

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
              <option value="Active">Active</option>
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
              <option value="Active">Active</option>
              <option value="Pending">Pending</option>
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
              <option value="MARA">Mara Basin</option>
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
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Id</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Form</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Basin/Site</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Date</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Submitted by</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">Status</TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className="divide-y divide-slate-100 text-sm text-slate-700">
            {paginatedSubmissions.map((sub) => (
              <TableRow key={sub.id} className="hover:bg-slate-50/50 transition-colors">
                <TableCell className="py-4 px-6 font-medium text-slate-900">{sub.id}</TableCell>
                <TableCell className="py-4 px-6">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                    {sub.formType}
                  </span>
                </TableCell>
                <TableCell className="py-4 px-6">{sub.basinSite}</TableCell>
                <TableCell className="py-4 px-6 font-semibold text-slate-900">{sub.date}</TableCell>
                <TableCell className="py-4 px-6">
                  <div className="flex flex-col">
                    <span className="font-semibold text-slate-900">{sub.submittedBy.name}</span>
                    <span className="text-xs text-slate-400 mt-0.5">{sub.submittedBy.email}</span>
                  </div>
                </TableCell>
                <TableCell className="py-4 px-6">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      sub.status === 'Active' || sub.status === 'Approved'
                        ? 'bg-green-50 text-green-700 border-green-100'
                        : sub.status === 'Pending'
                        ? 'bg-orange-50 text-orange-700 border-orange-100'
                        : 'bg-red-50 text-red-700 border-red-100'
                    }`}
                  >
                    {sub.status}
                  </span>
                </TableCell>
                <TableCell className="py-4 px-6 text-right">
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => handleReject(sub.id)}
                      className="px-3.5 py-1.5 border border-sky-400 hover:bg-sky-50 text-sky-500 rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer"
                    >
                      Reject
                    </button>
                    <button
                      type="button"
                      onClick={() => handleApprove(sub.id)}
                      className="px-3.5 py-1.5 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-xs font-bold transition-colors shadow-sm cursor-pointer"
                    >
                      Approve
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {paginatedSubmissions.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-slate-400">
                  No submissions found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination Controls */}
        {filteredSubmissions.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing <span className="font-semibold text-slate-700">{startIndex + 1}</span> to{" "}
              <span className="font-semibold text-slate-700">
                {Math.min(startIndex + pageSize, filteredSubmissions.length)}
              </span>{" "}
              of <span className="font-semibold text-slate-700">{filteredSubmissions.length}</span> submissions
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
                onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
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
