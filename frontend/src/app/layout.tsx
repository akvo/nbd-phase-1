import React from "react";
import "./globals.css";
import "leaflet/dist/leaflet.css";

export const metadata = {
  title: "Nbd Pilot",
  description: "Multi-service pilot platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  );
}
