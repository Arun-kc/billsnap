import type { Metadata } from "next";
import { Manrope, Urbanist } from "next/font/google";
import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

const urbanist = Urbanist({
  subsets: ["latin"],
  variable: "--font-urbanist",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BillSnap — Snap a Bill, Export to Excel | India",
  description:
    "Stop typing bills by hand. BillSnap turns your bill photos into ready-to-share Excel sheets — in minutes. Built for Indian shop owners. Join the waitlist.",
  metadataBase: new URL("https://billsnap.in"),
  alternates: {
    canonical: "https://billsnap.in/",
  },
  openGraph: {
    title: "BillSnap — Your Bills, Done in Minutes",
    description:
      "Snap a photo of any bill. BillSnap reads it and builds your Excel sheet automatically. No typing. No quarterly crunch. Made for Indian shop owners.",
    url: "https://billsnap.in/",
    siteName: "BillSnap",
    locale: "en_IN",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "BillSnap — Your Bills, Done in Minutes",
    description:
      "Snap a photo of any bill. BillSnap reads it and builds your Excel sheet automatically. No typing. No quarterly crunch. Made for Indian shop owners.",
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "BillSnap",
  url: "https://billsnap.in",
  description:
    "BillSnap turns bill photos into Excel sheets for Indian small shop owners. No manual entry required.",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web, Android, iOS",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "INR",
    availability: "https://schema.org/PreOrder",
    description: "Free early access — join the waitlist",
  },
  provider: {
    "@type": "Organization",
    name: "BillSnap",
    url: "https://billsnap.in",
    areaServed: { "@type": "Country", name: "India" },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-IN" className={`${manrope.variable} ${urbanist.variable}`}>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
