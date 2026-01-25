import type { Metadata } from "next";
import { Inter, Merienda } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";
import { LoadingScreen } from "@/components/effects/loading-screen";
import { DustBackground } from "@/components/ui/dust-background";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
});

const script = Merienda({
    subsets: ["latin"],
    weight: ["400", "600", "900"],
    variable: "--font-script",
    display: "swap",
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
        <html lang="en" className={`dark ${script.variable}`} suppressHydrationWarning>
            <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100`} suppressHydrationWarning>
                <div className="fixed inset-0 pointer-events-none overflow-hidden z-0" aria-hidden="true">
                    <div
                        className="absolute top-0 left-1/4 w-[700px] h-[700px] bg-gradient-to-r from-zinc-200/12 via-zinc-400/10 to-zinc-200/12 rounded-full blur-[150px] animate-pulse"
                        style={{ animationDuration: "6s" }}
                    />
                    <div
                        className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-gradient-to-r from-zinc-300/10 via-zinc-500/10 to-zinc-300/10 rounded-full blur-[150px] animate-pulse"
                        style={{ animationDuration: "8s" }}
                    />
                    <div
                        className="absolute top-1/3 right-1/3 w-[500px] h-[500px] bg-gradient-to-br from-zinc-200/10 via-transparent to-zinc-400/10 rounded-full blur-[120px] animate-pulse"
                        style={{ animationDuration: "10s" }}
                    />
                </div>
                <DustBackground />
                <LoadingScreen />
                <div className="noise" aria-hidden="true" />
                <div className="relative z-10">
                    <Providers>
                        {children}
                        <Toaster position="top-right" theme="dark" richColors />
                    </Providers>
                </div>
            </body>
        </html>
    );
}
