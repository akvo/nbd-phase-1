"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import {
  Edit2,
  Trash2,
  X,
  AlertTriangle,
  ChevronDown,
  Search,
  MapPin,
  Eye,
  Activity,
  Droplets,
  Leaf,
  Fish,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";

// Dynamic import for map to avoid SSR issues
const MapPicker = dynamic(() => import("./map-picker"), {
  ssr: false,
  loading: () => (
    <div className="h-64 bg-slate-100 rounded-lg flex items-center justify-center text-slate-400">
      Loading map...
    </div>
  ),
});

interface MetricEntry {
  value: string | number;
  unit: string | null;
  status: string;
  label: string;
  icon: string | null;
}

interface GroupScoreEntry {
  score: number;
  label: string;
  icon: string | null;
}

interface IkSignal {
  fish_abundance: string;
  water_clarity: string;
  vegetation_cover: string;
  pollution_events: string;
  encoded_signal_value: number;
}

interface SiteStatus {
  composite_score: number;
  ik_adjusted_score: number;
  traffic_light: string;
  health_class: string;
  sampling_date: string | null;
  metrics: Record<string, MetricEntry>;
  score_breakdown: Record<string, GroupScoreEntry>;
  ik_signal: IkSignal | null;
}

interface ManagementAction {
  label: string;
  description: string;
}

interface Site {
  id: string;
  code: string;
  wetland_id: string;
  name: string;
  description: string | null;
  geom: {
    type: string;
    coordinates: [number, number];
  };
  country?: string;
}

interface SiteDetails extends Site {
  status: SiteStatus | null;
  management_actions: ManagementAction[];
}

interface Wetland {
  id: string;
  name: string;
  parent_id: string;
}

interface SiteFormData {
  code: string;
  wetland_id: string;
  name: string;
  description: string;
  lat: string;
  lng: string;
}

const initialFormData: SiteFormData = {
  code: "",
  wetland_id: "",
  name: "",
  description: "",
  lat: "",
  lng: "",
};

export default function SiteManagementPage() {
  const [sites, setSites] = useState<Site[]>([]);
  const [wetlands, setWetlands] = useState<Wetland[]>([]);
  const [loading, setLoading] = useState(true);

  // Search and filter
  const [searchQuery, setSearchQuery] = useState("");

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [deleteModal, setDeleteModal] = useState<Site | null>(null);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [viewingSite, setViewingSite] = useState<SiteDetails | null>(null);
  const [viewLoading, setViewLoading] = useState(false);

  // Form state
  const [formData, setFormData] = useState<SiteFormData>(initialFormData);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);

  const fetchSites = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<Site[]>("/sites");
      setSites(res.data);
    } catch (err) {
      console.error("Failed to fetch sites:", err);
      setSites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchWetlands = useCallback(async () => {
    try {
      const res = await apiClient.get<Wetland[]>("/reference/wetlands");
      setWetlands(res.data);
    } catch (err) {
      console.error("Failed to fetch wetlands:", err);
      setWetlands([]);
    }
  }, []);

  useEffect(() => {
    fetchSites();
    fetchWetlands();
  }, [fetchSites, fetchWetlands]);

  // Filter sites by search query
  const filteredSites = useMemo(() => {
    if (!searchQuery.trim()) return sites;
    const query = searchQuery.toLowerCase();
    return sites.filter(
      (site) =>
        site.name.toLowerCase().includes(query) ||
        site.code.toLowerCase().includes(query)
    );
  }, [sites, searchQuery]);

  // Pagination
  const totalPages = Math.ceil(filteredSites.length / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedSites = filteredSites.slice(startIndex, startIndex + pageSize);

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const handleClear = () => {
    setSearchQuery("");
    setCurrentPage(1);
  };

  // View site details
  const handleViewClick = async (site: Site) => {
    setViewLoading(true);
    try {
      const res = await apiClient.get<SiteDetails>(`/sites/${site.id}`);
      setViewingSite(res.data);
    } catch (err) {
      console.error("Failed to fetch site details:", err);
    } finally {
      setViewLoading(false);
    }
  };

  const handleCloseViewModal = () => {
    setViewingSite(null);
  };

  // Create site
  const handleCreateClick = useCallback(() => {
    setFormData(initialFormData);
    setFormError("");
    setShowCreateModal(true);
  }, []);

  // Listen for add site event from layout header
  useEffect(() => {
    const handleAddSiteEvent = () => {
      handleCreateClick();
    };
    window.addEventListener("open-add-site-modal", handleAddSiteEvent);
    return () => {
      window.removeEventListener("open-add-site-modal", handleAddSiteEvent);
    };
  }, [handleCreateClick]);

  // Edit site
  const handleEditClick = (site: Site) => {
    setFormData({
      code: site.code,
      wetland_id: site.wetland_id,
      name: site.name,
      description: site.description || "",
      lat: site.geom.coordinates[1].toString(),
      lng: site.geom.coordinates[0].toString(),
    });
    setFormError("");
    setEditingSite(site);
  };

  // Delete site
  const handleDeleteClick = (site: Site) => {
    setDeleteModal(site);
    setDeleteConfirmText("");
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal || deleteConfirmText !== "DELETE") return;

    setDeleteLoading(true);
    try {
      await apiClient.delete(`/sites/${deleteModal.id}`);
      setSites((prev) => prev.filter((s) => s.id !== deleteModal.id));
      setDeleteModal(null);
      setDeleteConfirmText("");
    } catch (err) {
      console.error("Failed to delete site:", err);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleCloseDeleteModal = () => {
    setDeleteModal(null);
    setDeleteConfirmText("");
  };

  // Form submit (create or update)
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormLoading(true);
    setFormError("");

    const lat = parseFloat(formData.lat);
    const lng = parseFloat(formData.lng);

    if (isNaN(lat) || isNaN(lng)) {
      setFormError("Please enter valid coordinates");
      setFormLoading(false);
      return;
    }

    const payload = {
      code: formData.code,
      wetland_id: formData.wetland_id,
      name: formData.name,
      description: formData.description || null,
      geom: {
        type: "Point",
        coordinates: [lng, lat],
      },
    };

    try {
      if (editingSite) {
        await apiClient.put(`/sites/${editingSite.id}`, payload);
      } else {
        await apiClient.post("/sites", payload);
      }
      setShowCreateModal(false);
      setEditingSite(null);
      setFormData(initialFormData);
      fetchSites();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setFormError(error.response?.data?.detail || "Failed to save site");
    } finally {
      setFormLoading(false);
    }
  };

  const handleCloseFormModal = () => {
    setShowCreateModal(false);
    setEditingSite(null);
    setFormData(initialFormData);
    setFormError("");
  };

  const handleMapClick = (lat: number, lng: number) => {
    setFormData((prev) => ({
      ...prev,
      lat: lat.toFixed(6),
      lng: lng.toFixed(6),
    }));
  };

  const getWetlandName = (wetlandId: string) => {
    const wetland = wetlands.find((w) => w.id === wetlandId);
    return wetland?.name || wetlandId;
  };

  return (
    <div className="space-y-6">
      {/* Search and Controls Row */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
        <div className="flex-1 flex items-center gap-4">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name or code..."
              className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
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

      {/* Sites Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Code
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Name
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Wetland
              </TableHead>
              <TableHead className="py-4 px-6 text-xs font-semibold text-slate-500 tracking-wider">
                Coordinates
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
                  colSpan={5}
                  className="py-8 text-center text-slate-400"
                >
                  Loading sites...
                </TableCell>
              </TableRow>
            ) : paginatedSites.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={5}
                  className="py-8 text-center text-slate-400"
                >
                  {searchQuery
                    ? "No sites found matching your search."
                    : "No sites found."}
                </TableCell>
              </TableRow>
            ) : (
              paginatedSites.map((site) => (
                <TableRow
                  key={site.id}
                  className="hover:bg-slate-50/50 transition-colors"
                >
                  <TableCell className="py-4 px-6 font-mono text-slate-500">
                    {site.code}
                  </TableCell>
                  <TableCell className="py-4 px-6 font-semibold text-slate-900">
                    {site.name}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-slate-600">
                    {getWetlandName(site.wetland_id)}
                  </TableCell>
                  <TableCell className="py-4 px-6 font-mono text-xs text-slate-500">
                    {site.geom.coordinates[1].toFixed(4)},{" "}
                    {site.geom.coordinates[0].toFixed(4)}
                  </TableCell>
                  <TableCell className="py-4 px-6 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        type="button"
                        onClick={() => handleViewClick(site)}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-sky-200 hover:bg-sky-50 text-sky-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>View</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEditClick(site)}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-medium transition-colors cursor-pointer"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteClick(site)}
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

        {/* Pagination Controls */}
        {filteredSites.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <div className="text-xs text-slate-500">
              Showing{" "}
              <span className="font-semibold text-slate-700">
                {startIndex + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-700">
                {Math.min(startIndex + pageSize, filteredSites.length)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-700">
                {filteredSites.length}
              </span>{" "}
              sites
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

      {/* Create/Edit Modal */}
      {(showCreateModal || editingSite) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-slate-900">
                <MapPin className="w-5 h-5" />
                <h2 className="text-lg font-semibold">
                  {editingSite ? "Edit Site" : "Add New Site"}
                </h2>
              </div>
              <button
                type="button"
                onClick={handleCloseFormModal}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleFormSubmit} className="p-6 space-y-5">
              {formError && (
                <div className="bg-red-50 text-red-700 text-sm px-4 py-3 rounded-lg">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Site Code
                  </label>
                  <input
                    type="text"
                    value={formData.code}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, code: e.target.value }))
                    }
                    required
                    placeholder="e.g., NBD-MARA-001"
                    className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Wetland
                  </label>
                  <div className="relative">
                    <select
                      value={formData.wetland_id}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          wetland_id: e.target.value,
                        }))
                      }
                      required
                      className="w-full appearance-none bg-white border border-slate-200 rounded-lg px-4 py-2.5 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all cursor-pointer"
                    >
                      <option value="">Select wetland...</option>
                      {wetlands.map((w) => (
                        <option key={w.id} value={w.id}>
                          {w.name}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Site Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                  required
                  placeholder="e.g., Lower Mara Wetland Site 1"
                  className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Description <span className="text-slate-400">(optional)</span>
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Brief description of the monitoring site..."
                  rows={2}
                  className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all resize-none"
                />
              </div>

              {/* Coordinates */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Location
                </label>
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Latitude
                    </label>
                    <input
                      type="text"
                      value={formData.lat}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          lat: e.target.value,
                        }))
                      }
                      required
                      placeholder="-1.2345"
                      className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-500 mb-1">
                      Longitude
                    </label>
                    <input
                      type="text"
                      value={formData.lng}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          lng: e.target.value,
                        }))
                      }
                      required
                      placeholder="34.5678"
                      className="w-full border border-slate-200 rounded-lg px-4 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all"
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500 mb-2">
                  Click on the map to set location, or enter coordinates
                  manually.
                </p>
                <div className="h-64 rounded-lg overflow-hidden border border-slate-200">
                  <MapPicker
                    lat={parseFloat(formData.lat) || -1.5}
                    lng={parseFloat(formData.lng) || 34.5}
                    onMapClick={handleMapClick}
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleCloseFormModal}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="inline-flex items-center space-x-2 px-5 py-2 bg-sky-500 text-white rounded-lg text-sm font-medium hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  {formLoading ? (
                    <span>Saving...</span>
                  ) : (
                    <>
                      <MapPin className="w-4 h-4" />
                      <span>
                        {editingSite ? "Save Changes" : "Create Site"}
                      </span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Details Modal */}
      {(viewingSite || viewLoading) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl mx-4 overflow-hidden max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <div className="flex items-center space-x-2 text-slate-900">
                <Eye className="w-5 h-5" />
                <h2 className="text-lg font-semibold">Site Details</h2>
              </div>
              <button
                type="button"
                onClick={handleCloseViewModal}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {viewLoading ? (
              <div className="p-12 text-center text-slate-400">
                Loading site details...
              </div>
            ) : viewingSite ? (
              <div className="p-6 space-y-6">
                {/* Basic Info */}
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                      Basic Information
                    </h3>
                    <div className="space-y-3">
                      <div>
                        <span className="text-xs text-slate-400">Name</span>
                        <p className="font-semibold text-slate-900">
                          {viewingSite.name}
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400">Code</span>
                        <p className="font-mono text-slate-700">
                          {viewingSite.code}
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400">Country</span>
                        <p className="text-slate-700">
                          {viewingSite.country || "-"}
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400">Wetland</span>
                        <p className="text-slate-700">
                          {getWetlandName(viewingSite.wetland_id)}
                        </p>
                      </div>
                      <div>
                        <span className="text-xs text-slate-400">
                          Coordinates
                        </span>
                        <p className="font-mono text-sm text-slate-700">
                          {viewingSite.geom.coordinates[1].toFixed(6)},{" "}
                          {viewingSite.geom.coordinates[0].toFixed(6)}
                        </p>
                      </div>
                      {viewingSite.description && (
                        <div>
                          <span className="text-xs text-slate-400">
                            Description
                          </span>
                          <p className="text-slate-700 text-sm">
                            {viewingSite.description}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Health Status */}
                  {viewingSite.status && (
                    <div>
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                        Health Status
                      </h3>
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg ${
                              viewingSite.status.health_class === "A" ||
                              viewingSite.status.health_class === "B"
                                ? "bg-green-500"
                                : viewingSite.status.health_class === "C"
                                  ? "bg-amber-500"
                                  : "bg-red-500"
                            }`}
                          >
                            {viewingSite.status.health_class}
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900">
                              {viewingSite.status.traffic_light} Status
                            </p>
                            <p className="text-xs text-slate-500">
                              Health Class {viewingSite.status.health_class}
                            </p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-slate-50 rounded-lg p-3">
                            <span className="text-xs text-slate-400">
                              Composite Score
                            </span>
                            <p className="font-semibold text-lg text-slate-900">
                              {(
                                viewingSite.status.composite_score * 100
                              ).toFixed(1)}
                              %
                            </p>
                          </div>
                          <div className="bg-slate-50 rounded-lg p-3">
                            <span className="text-xs text-slate-400">
                              IK Adjusted
                            </span>
                            <p className="font-semibold text-lg text-slate-900">
                              {(
                                viewingSite.status.ik_adjusted_score * 100
                              ).toFixed(1)}
                              %
                            </p>
                          </div>
                        </div>
                        {viewingSite.status.sampling_date && (
                          <div>
                            <span className="text-xs text-slate-400">
                              Last Sampling
                            </span>
                            <p className="text-slate-700">
                              {new Date(
                                viewingSite.status.sampling_date
                              ).toLocaleDateString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Score Breakdown */}
                {viewingSite.status &&
                  Object.keys(viewingSite.status.score_breakdown).length >
                    0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                        Score Breakdown
                      </h3>
                      <div className="grid grid-cols-3 gap-3">
                        {Object.entries(viewingSite.status.score_breakdown).map(
                          ([key, entry]) => (
                            <div
                              key={key}
                              className="bg-slate-50 rounded-lg p-3"
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <Activity className="w-4 h-4 text-slate-400" />
                                <span className="text-xs text-slate-500">
                                  {entry.label}
                                </span>
                              </div>
                              <p className="font-semibold text-slate-900">
                                {(entry.score * 100).toFixed(1)}%
                              </p>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Metrics */}
                {viewingSite.status &&
                  Object.keys(viewingSite.status.metrics).length > 0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                        Metrics
                      </h3>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {Object.entries(viewingSite.status.metrics).map(
                          ([key, metric]) => (
                            <div
                              key={key}
                              className="bg-slate-50 rounded-lg p-3 border border-slate-100"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-slate-500">
                                  {metric.label}
                                </span>
                                <span
                                  className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                    metric.status === "Normal"
                                      ? "bg-green-100 text-green-700"
                                      : metric.status === "Warning"
                                        ? "bg-amber-100 text-amber-700"
                                        : "bg-red-100 text-red-700"
                                  }`}
                                >
                                  {metric.status}
                                </span>
                              </div>
                              <p className="font-semibold text-slate-900">
                                {metric.value}
                                {metric.unit && (
                                  <span className="text-xs text-slate-400 ml-1">
                                    {metric.unit}
                                  </span>
                                )}
                              </p>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Indigenous Knowledge Signal */}
                {viewingSite.status?.ik_signal && (
                  <div>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                      Indigenous Knowledge Signal
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Fish className="w-4 h-4 text-blue-500" />
                          <span className="text-xs text-blue-600">
                            Fish Abundance
                          </span>
                        </div>
                        <p className="font-semibold text-blue-900">
                          {viewingSite.status.ik_signal.fish_abundance}
                        </p>
                      </div>
                      <div className="bg-cyan-50 rounded-lg p-3 border border-cyan-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Droplets className="w-4 h-4 text-cyan-500" />
                          <span className="text-xs text-cyan-600">
                            Water Clarity
                          </span>
                        </div>
                        <p className="font-semibold text-cyan-900">
                          {viewingSite.status.ik_signal.water_clarity}
                        </p>
                      </div>
                      <div className="bg-green-50 rounded-lg p-3 border border-green-100">
                        <div className="flex items-center gap-2 mb-1">
                          <Leaf className="w-4 h-4 text-green-500" />
                          <span className="text-xs text-green-600">
                            Vegetation
                          </span>
                        </div>
                        <p className="font-semibold text-green-900">
                          {viewingSite.status.ik_signal.vegetation_cover}
                        </p>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
                        <div className="flex items-center gap-2 mb-1">
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                          <span className="text-xs text-amber-600">
                            Pollution
                          </span>
                        </div>
                        <p className="font-semibold text-amber-900">
                          {viewingSite.status.ik_signal.pollution_events}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 bg-slate-50 rounded-lg p-3">
                      <span className="text-xs text-slate-400">
                        Encoded Signal Value
                      </span>
                      <p className="font-semibold text-slate-900">
                        {viewingSite.status.ik_signal.encoded_signal_value.toFixed(
                          3
                        )}
                      </p>
                    </div>
                  </div>
                )}

                {/* Management Actions */}
                {viewingSite.management_actions &&
                  viewingSite.management_actions.length > 0 && (
                    <div>
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                        Recommended Management Actions
                      </h3>
                      <div className="space-y-2">
                        {viewingSite.management_actions.map((action, idx) => (
                          <div
                            key={idx}
                            className="bg-amber-50 border border-amber-100 rounded-lg p-3"
                          >
                            <p className="font-medium text-amber-900">
                              {action.label}
                            </p>
                            <p className="text-sm text-amber-700 mt-1">
                              {action.description}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {/* No Status Message */}
                {!viewingSite.status && (
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-6 text-center">
                    <p className="text-slate-500">
                      No health status data available for this site yet.
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Status data will appear after monitoring submissions are
                      processed.
                    </p>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center space-x-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                <h2 className="text-lg font-semibold">Delete Site</h2>
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
                  <span className="font-semibold">{deleteModal.name}</span>{" "}
                  <span className="font-mono text-xs">
                    ({deleteModal.code})
                  </span>
                  . This action cannot be undone and will permanently remove the
                  site and all associated data.
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
                      <span>Delete Site</span>
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
