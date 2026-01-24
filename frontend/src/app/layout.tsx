import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";
import { LoadingScreen } from "@/components/effects/loading-screen";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
});

export const metadata: Metadata = {
    title: "GraphGuard | Real-Time Fraud Intelligence",
    description: "Portfolio-grade fraud detection with graph analytics, ML training pipelines, and an investigator RAG assistant.",
    keywords: ["fraud detection", "graph analytics", "machine learning", "real-time", "financial security"],
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark" suppressHydrationWarning>
            <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100`} suppressHydrationWarning>
                <LoadingScreen />
                <Providers>
                    {children}
                    <Toaster position="top-right" theme="dark" richColors />
                </Providers>
            </body>
        </html>
    );
}
