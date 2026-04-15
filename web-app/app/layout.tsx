import type { Metadata, Viewport } from "next";
import { Urbanist, Manrope } from "next/font/google";
import "./globals.css";

const urbanist = Urbanist({
  variable: "--font-urbanist",
  subsets: ["latin"],
  display: "swap",
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "BillSnap — Snap a bill. Done.",
  description: "Digitize your shop bills in seconds. No typing, no hassle.",
  applicationName: "BillSnap",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#5c2d91",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${urbanist.variable} ${manrope.variable} h-full`}
    >
      <body className="min-h-dvh flex flex-col">{children}</body>
    </html>
  );
}
