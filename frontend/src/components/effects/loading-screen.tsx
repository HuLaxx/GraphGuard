"use client";

import { useEffect, useState } from "react";

export function LoadingScreen() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        try {
            const alreadyShown = sessionStorage.getItem("gg_loaded");
            if (alreadyShown) return;
            sessionStorage.setItem("gg_loaded", "1");
        } catch {
            // If sessionStorage is blocked, still show once per mount.
        }

        setIsVisible(true);
        const hideTimer = setTimeout(() => setIsVisible(false), 2200);
        return () => clearTimeout(hideTimer);
    }, []);

    if (!isVisible) return null;

    return (
        <div
            className="loading-screen fixed inset-0 z-[100] flex flex-col items-center justify-center bg-zinc-950"
        >
            {/* Background glow */}
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-zinc-200/10 via-zinc-400/10 to-white/10 rounded-full blur-[150px] animate-pulse" />
                <div className="absolute top-1/4 left-1/4 w-[300px] h-[300px] bg-gradient-to-r from-zinc-400/10 to-zinc-600/10 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: "0.3s" }} />
                <div className="absolute bottom-1/4 right-1/4 w-[250px] h-[250px] bg-gradient-to-r from-zinc-200/10 to-white/10 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: "0.6s" }} />
            </div>

            <div className="relative z-10 flex flex-col items-center">
                {/* Logo */}
                <div className="relative mb-8">
                    <div className="w-20 h-20 rounded-2xl overflow-hidden shadow-2xl shadow-white/20 animate-pulse">
                        <img src="/icon.svg" alt="GraphGuard" className="w-full h-full object-cover" />
                    </div>
                    <div className="absolute -inset-2 rounded-3xl bg-gradient-to-r from-zinc-200 via-white to-zinc-300 opacity-20 blur-xl animate-pulse" />
                </div>

                <h1 className="text-3xl md:text-4xl font-bold mb-4 bg-gradient-to-r from-zinc-100 via-zinc-300 to-white bg-clip-text text-transparent">
                    GraphGuard
                </h1>
                <p className="text-zinc-500 text-sm mb-8 tracking-wide">
                    Fraud Intelligence Platform
                </p>

                <div className="relative">
                    <div className="w-48 h-1 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                            className="progress-bar h-full bg-gradient-to-r from-zinc-200 via-white to-zinc-300 rounded-full"
                        />
                    </div>
                </div>

                <div className="flex gap-2 mt-6">
                    {[0, 1, 2].map((i) => (
                        <div
                            key={i}
                            className="w-2 h-2 rounded-full bg-zinc-300/60 animate-pulse"
                            style={{ animationDelay: `${i * 0.2}s` }}
                        />
                    ))}
                </div>
            </div>

            <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />

            <style jsx>{`
                .loading-screen {
                    animation: screenExit 2.1s cubic-bezier(0.76, 0, 0.24, 1) forwards;
                }

                .progress-bar {
                    width: 0%;
                    animation: loadProgress 1.4s ease-out forwards;
                }

                @keyframes screenExit {
                    0% {
                        transform: translateY(0);
                        opacity: 1;
                        visibility: visible;
                    }
                    66% {
                        transform: translateY(0);
                        opacity: 1;
                        visibility: visible;
                    }
                    100% {
                        transform: translateY(-100%);
                        opacity: 0;
                        visibility: hidden;
                    }
                }

                @keyframes loadProgress {
                    0% { width: 0%; }
                    50% { width: 70%; }
                    100% { width: 100%; }
                }
            `}</style>
        </div>
    );
}
