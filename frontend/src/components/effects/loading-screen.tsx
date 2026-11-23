'use client';

import { useEffect, useState } from 'react';

/*
 * First-load sequence: a network of nodes draws itself into the GraphGuard shield,
 * the wordmark rises, then the curtain lifts. It runs on every full page load and
 * is driven by CSS, so it covers the first paint even before hydration. Client-side
 * navigation never replays it (the layout persists).
 */

// Shield outline from the app icon (32-unit grid), scaled to a 224 box.
const rim = [
    [112, 38],
    [170, 66],
    [170, 112],
    [154, 154],
    [112, 186],
    [70, 154],
    [54, 112],
    [54, 66],
];
const core = [
    [112, 92],
    [88, 128],
    [136, 128],
];
const spokes: Array<[number[], number[]]> = [
    [rim[0], core[0]],
    [rim[1], core[0]],
    [rim[7], core[0]],
    [core[0], core[1]],
    [core[0], core[2]],
    [core[1], core[2]],
    [rim[6], core[1]],
    [rim[5], core[1]],
    [rim[2], core[2]],
    [rim[3], core[2]],
    [rim[4], core[1]],
    [rim[4], core[2]],
];
const rimPath = `M${rim.map((p) => p.join(' ')).join(' L')} Z`;

const TOTAL_MS = 2600;

export function LoadingScreen() {
    const [mounted, setMounted] = useState(true);

    useEffect(() => {
        const done = () => {
            document.documentElement.dataset.ggLoaded = 'true';
            setMounted(false);
        };
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const timer = window.setTimeout(done, reduce ? 700 : TOTAL_MS);
        return () => window.clearTimeout(timer);
    }, []);

    if (!mounted) return null;

    return (
        <div className="gg-loader" role="status" aria-label="Loading GraphGuard">
            <div className="gg-loader__glow" aria-hidden="true" />
            <div className="gg-loader__center">
                <svg className="gg-loader__mark" viewBox="0 0 224 224" aria-hidden="true">
                    <defs>
                        <linearGradient id="gg-loader-fill" x1="0" y1="0" x2="1" y2="1">
                            <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" />
                            <stop offset="1" stopColor="#71717a" stopOpacity="0.04" />
                        </linearGradient>
                    </defs>
                    <path className="gg-loader__fill" d={rimPath} fill="url(#gg-loader-fill)" />
                    {spokes.map(([a, b], i) => (
                        <line
                            key={i}
                            className="gg-loader__spoke"
                            x1={a[0]}
                            y1={a[1]}
                            x2={b[0]}
                            y2={b[1]}
                            pathLength={1}
                            style={{ animationDelay: `${380 + i * 45}ms` }}
                        />
                    ))}
                    <path className="gg-loader__rim" d={rimPath} pathLength={1} />
                    {[...rim, ...core].map(([x, y], i) => (
                        <circle
                            key={`${x}-${y}`}
                            className={i >= rim.length ? 'gg-loader__node gg-loader__node--core' : 'gg-loader__node'}
                            cx={x}
                            cy={y}
                            r={i >= rim.length ? 5 : 4}
                            style={{ animationDelay: `${i * 55}ms`, transformOrigin: `${x}px ${y}px` }}
                        />
                    ))}
                </svg>
                <p className="gg-loader__word">GraphGuard</p>
                <p className="gg-loader__line">Graph-based fraud investigation</p>
            </div>
            <p className="gg-loader__credit" aria-hidden="true">
                <span className="hulax-credit-label">A Project By</span> <span className="hulax-credit hulax-credit-gradient">HuLaX</span>
            </p>
            <div className="gg-loader__edge" aria-hidden="true" />
        </div>
    );
}
