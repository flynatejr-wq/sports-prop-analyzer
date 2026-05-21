import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import MobileAwareLayout from "@/components/layout/MobileAwareLayout";
import ToastContainer from "@/components/ui/Toast";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PropEdge AI — Sports Prop Intelligence",
  description:
    "Real-time AI-powered sports prop EV analysis. Find the best bets before the lines move.",
  keywords: ["sports betting", "prop bets", "EV calculator", "PrizePicks", "DraftKings"],
  viewport: "width=device-width, initial-scale=1, maximum-scale=1",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-background text-white antialiased`}>
        <MobileAwareLayout>{children}</MobileAwareLayout>
        <ToastContainer />
      </body>
    </html>
  );
}
