"use client";

import React from "react";
import Link from "next/link";
import { Database, MapPin, ArrowRight } from "lucide-react";

export default function AdminLandingPage() {
  const cards = [
    {
      title: "Data & Curation",
      description:
        "Review, approve, or reject incoming citizen monitoring reports and laboratory QA samples.",
      href: "/admin/data",
      icon: Database,
      color: "text-sky-500 bg-sky-50 border-sky-100",
    },
    {
      title: "Resource Management",
      description:
        "Define monitoring sites, check boundaries, and configure PostGIS-referenced basins and wetlands.",
      href: "/admin/resources",
      icon: MapPin,
      color: "text-purple-500 bg-purple-50 border-purple-100",
    },
  ];

  return (
    <div className="space-y-8 w-full">
      {/* Welcome Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <h2 className="text-xl font-bold text-slate-900">
            Welcome to Nile Voice Admin Portal
          </h2>
          <p className="text-slate-500 text-sm max-w-xl">
            This workspace provides tools to moderate citizen science ingestion
            channels, manage access roles, and audit compliance logs for the
            Mara and Sio-Siteko basins.
          </p>
        </div>
        <Link
          href="/admin/data"
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-sky-500 text-white rounded-lg text-sm font-semibold hover:bg-sky-600 transition-colors shadow-sm self-start md:self-auto shrink-0"
        >
          <span>Go to Data Overview</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Admin Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="space-y-4">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center border ${card.color}`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h3 className="font-bold text-slate-900 text-base">
                    {card.title}
                  </h3>
                  <p className="text-slate-500 text-xs leading-relaxed">
                    {card.description}
                  </p>
                </div>
              </div>

              <Link
                href={card.href}
                className="mt-6 inline-flex items-center space-x-1 text-xs font-bold text-sky-500 hover:text-sky-600 self-start group"
              >
                <span>Manage</span>
                <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
