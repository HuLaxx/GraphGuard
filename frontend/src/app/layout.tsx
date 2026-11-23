import type { Metadata } from "next";
import { Archivo, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import "./casefile.css";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";
import { LoadingScreen } from "@/components/effects/loading-screen";

const archivo = Archivo({
    subsets: ["latin"],
    axes: ["wdth"],
    variable: "--font-archivo",
    display: "swap",
});

const sourceSerif = Source_Serif_4({
    subsets: ["latin"],
    variable: "--font-source-serif",
    display: "swap",
});

export const metadata: Metadata = {
    title: "GraphGuard | Graph-based fraud investigation",
    description:
        "Follows payments into a graph of accounts, devices and merchants, scores them with an explainable model behind a release gate, and builds a case an analyst can check. Synthetic data only.",
    keywords: ["fraud detection", "graph analytics", "Neo4j", "Kafka", "XGBoost", "SHAP", "MLflow"],
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className={`dark ${archivo.variable} ${sourceSerif.variable}`} suppressHydrationWarning>
            <body className="font-sans antialiased" suppressHydrationWarning>
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
