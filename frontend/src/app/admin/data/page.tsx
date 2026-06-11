'use client';

import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface Submission {
  id: string;
  formType: string;
  basinSite: string;
  date: string;
  submittedBy: {
    name: string;
    email: string;
  };
  status: 'Active' | 'Pending' | 'Rejected';
}

const initialSubmissions: Submission[] = [
  {
    id: 'PE-20260508-041',
    formType: 'Active',
    basinSite: 'NBD-MARA-001',
    date: '12.04.80',
    submittedBy: { name: 'Rosemarie Ondricka-Haley', email: 'Theresa.Cormier7@hotmail.com' },
    status: 'Active',
  },
  {
    id: 'PE-20260508-042',
    formType: 'Active',
    basinSite: 'NBD-MARA-002',
    date: '12.04.80',
    submittedBy: { name: 'Arturo Kutch', email: 'Morris.Dach86@gmail.com' },
    status: 'Pending',
  },
  {
    id: 'PE-20260508-043',
    formType: 'Active',
    basinSite: 'NBD-MARA-003',
    date: '12.04.80',
    submittedBy: { name: 'Minnie Donnelly', email: 'Theresa.Cling84@gmail.com' },
    status: 'Pending',
  },
  {
    id: 'PE-20260508-044',
    formType: 'Active',
    basinSite: 'NBD-MARA-004',
    date: '12.04.80',
    submittedBy: { name: 'Doyle Johns', email: 'Jonathon.Doyle@hotmail.com' },
    status: 'Pending',
  },
  {
    id: 'PE-20260508-045',
    formType: 'Active',
    basinSite: 'NBD-MARA-005',
    date: '12.04.80',
    submittedBy: { name: 'Henrietta Stroman', email: 'Joanne1@hotmail.com' },
    status: 'Rejected',
  },
  {
    id: 'PE-20260508-046',
    formType: 'Active',
    basinSite: 'NBD-MARA-006',
    date: '12.04.80',
    submittedBy: { name: 'James Zulauf-Bode', email: 'Sam.Stiedemann@yahoo.com' },
    status: 'Rejected',
  },
];

export default function DataOverviewPage() {
  const [submissions, setSubmissions] = useState<Submission[]>(initialSubmissions);
  const [formFilter, setFormFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [basinFilter, setBasinFilter] = useState('');

  const handleApprove = (id: string) => {
    setSubmissions(prev =>
      prev.map(sub => (sub.id === id ? { ...sub, status: 'Active' as const } : sub))
    );
  };

  const handleReject = (id: string) => {
    setSubmissions(prev =>
      prev.map(sub => (sub.id === id ? { ...sub, status: 'Rejected' as const } : sub))
    );
  };

  const handleClear = () => {
    setFormFilter('');
    setStatusFilter('');
    setBasinFilter('');
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (formFilter && sub.formType !== formFilter) return false;
    if (statusFilter && sub.status !== statusFilter) return false;
    if (basinFilter && !sub.basinSite.includes(basinFilter)) return false;
    return true;
  });

  return (
    <div className="space-y-6">

      {/* Filtering Row Controls */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">

          {/* Form Filter */}
          <div className="relative">
            <select
              value={formFilter}
              onChange={(e) => setFormFilter(e.target.value)}
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
              onChange={(e) => setStatusFilter(e.target.value)}
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
              onChange={(e) => setBasinFilter(e.target.value)}
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
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 tracking-wider">
                <th className="py-4 px-6">Id</th>
                <th className="py-4 px-6">Form type</th>
                <th className="py-4 px-6">Basin/Site</th>
                <th className="py-4 px-6">Date</th>
                <th className="py-4 px-6">Submitted by</th>
                <th className="py-4 px-6">Status</th>
                <th className="py-4 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {filteredSubmissions.map((sub) => (
                <tr key={sub.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="py-4 px-6 font-medium text-slate-900">{sub.id}</td>
                  <td className="py-4 px-6">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                      {sub.formType}
                    </span>
                  </td>
                  <td className="py-4 px-6">{sub.basinSite}</td>
                  <td className="py-4 px-6 font-semibold text-slate-900">{sub.date}</td>
                  <td className="py-4 px-6">
                    <div className="flex flex-col">
                      <span className="font-semibold text-slate-900">{sub.submittedBy.name}</span>
                      <span className="text-xs text-slate-400 mt-0.5">{sub.submittedBy.email}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        sub.status === 'Active'
                          ? 'bg-green-50 text-green-700 border-green-100'
                          : sub.status === 'Pending'
                          ? 'bg-orange-50 text-orange-700 border-orange-100'
                          : 'bg-red-50 text-red-700 border-red-100'
                      }`}
                    >
                      {sub.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">
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
                  </td>
                </tr>
              ))}
              {filteredSubmissions.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No submissions found matching the filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
