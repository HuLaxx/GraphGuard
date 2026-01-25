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
                <div className="looming-gradient" aria-hidden="true" />
                <DustBackground />
                <LoadingScreen />
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
