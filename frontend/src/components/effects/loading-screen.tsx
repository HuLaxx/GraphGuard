'use client';

import { useEffect, useState } from 'react';
import { Wordmark } from '@/components/casefile/ring-graph';

/** A short brand mark on the first visit of a session. Skipped for reduced motion. */
export function LoadingScreen() {
    const [phase, setPhase] = useState<'hidden' | 'shown' | 'leaving'>('hidden');

    useEffect(() => {
        let seen = false;
        try {
            seen = sessionStorage.getItem('gg_opened') === '1';
            sessionStorage.setItem('gg_opened', '1');
        } catch {
            seen = false;
        }
        if (seen || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        const show = requestAnimationFrame(() => setPhase('shown'));
        const leave = window.setTimeout(() => setPhase('leaving'), 700);
        const hide = window.setTimeout(() => setPhase('hidden'), 980);
        return () => {
            cancelAnimationFrame(show);
            window.clearTimeout(leave);
            window.clearTimeout(hide);
        };
    }, []);

    if (phase === 'hidden') return null;

    return (
        <div className="gg-opening" data-leaving={phase === 'leaving'} aria-hidden="true">
            <div className="gg-opening__mark">
                <Wordmark />
                <span>GraphGuard</span>
            </div>
        </div>
    );
}
