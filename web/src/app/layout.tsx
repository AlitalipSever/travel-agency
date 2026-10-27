import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { SiteHeader } from "@/components/site/header";
import { SiteFooter } from "@/components/site/footer";

// Recursive (variable, OFL) for sentences and numbers; IBM Plex Mono (OFL) for labels and units.
const recursive = localFont({
  src: "./fonts/recursive-latin-full-normal.woff2",
  weight: "300 1000",
  variable: "--font-sans",
  display: "swap",
});

const plexMono = localFont({
  src: [
    { path: "./fonts/ibm-plex-mono-latin-400-normal.woff2", weight: "400" },
    { path: "./fonts/ibm-plex-mono-latin-700-normal.woff2", weight: "700" },
  ],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Travel agency backend", template: "%s | Travel agency backend" },
  description:
    "Weather, locations by temperature bracket, tour packages with a derived danger score, departures with capacity and the bookable search: a backend case study with its documentation and a live demo.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${recursive.variable} ${plexMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
