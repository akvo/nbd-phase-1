import React from "react";
import { Inter } from "next/font/google";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { AuthProvider } from "@/context/AuthContext";
import { DomainProvider } from "@/context/domain-context";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata = {
  title: "Nile Voice - Citizen-led Data Platform",
  description:
    "Citizen-led data generation and management platform for the Nile Basin",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      className={inter.variable}
      style={{ fontFamily: inter.style?.fontFamily }}
    >
      <body
        style={{ margin: 0, padding: 0, fontFamily: inter.style?.fontFamily }}
        className={inter.className}
      >
        <NextIntlClientProvider messages={messages}>
          <DomainProvider>
            <AuthProvider>{children}</AuthProvider>
          </DomainProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
