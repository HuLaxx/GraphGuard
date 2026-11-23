'use client';

import { useEffect, useId, useRef, useState } from 'react';

/*
 * The hero's investigation lens. A quiet network of accounts sits on the board.
 * Payments between accounts and merchants are always visible; the identity links
 * (shared phones, a shared top-up merchant) only appear inside the lens. Sweeping
 * the lens over a hidden link "finds" it; once every ring link is found the case
 * is flagged. Illustrative synthetic data, no model output.
 */

type Kind = 'account' | 'device' | 'merchant';
type GraphNode = { id: string; x: number; y: number; kind: Kind; label?: string; ring?: boolean };

const W = 640;
const H = 470;
const LENS_R = 92;

const ringNodes: GraphNode[] = [
    { id: 'a1', x: 236, y: 150, kind: 'account', label: 'acct 4417', ring: true },
    { id: 'a2', x: 196, y: 262, kind: 'account', label: 'acct 0932', ring: true },
    { id: 'a3', x: 300, y: 330, kind: 'account', label: 'acct 7710', ring: true },
    { id: 'a4', x: 372, y: 196, kind: 'account', label: 'acct 2268', ring: true },
    { id: 'a5', x: 338, y: 262, kind: 'account', label: 'acct 5091', ring: true },
    { id: 'd1', x: 300, y: 112, kind: 'device', label: 'phone d-09', ring: true },
    { id: 'd2', x: 228, y: 340, kind: 'device', label: 'phone d-31', ring: true },
    { id: 'm1', x: 448, y: 268, kind: 'merchant', label: 'top-up merchant', ring: true },
];

// Seeded scatter of ordinary customers and merchants around the ring.
function scatter(): GraphNode[] {
    let seed = 7;
    const rand = () => {
        seed = (seed * 16807) % 2147483647;
        return (seed - 1) / 2147483646;
    };
    const out: GraphNode[] = [];
    let tries = 0;
    while (out.length < 30 && tries < 2000) {
        tries += 1;
        const x = 34 + rand() * (W - 68);
        const y = 60 + rand() * (H - 100);
        const nearRing = ringNodes.some((n) => Math.hypot(n.x - x, n.y - y) < 54);
        const nearOther = out.some((n) => Math.hypot(n.x - x, n.y - y) < 46);
        if (nearRing || nearOther) continue;
        out.push({ id: `b${out.length}`, x, y, kind: out.length % 7 === 0 ? 'merchant' : 'account' });
    }
    return out;
}

const background = scatter();
const nodes = [...ringNodes, ...background];
const byId = new Map(nodes.map((n) => [n.id, n]));

// Ordinary payments: always visible, faint.
const payments: Array<[string, string]> = (() => {
    const merchants = background.filter((n) => n.kind === 'merchant');
    const pairs: Array<[string, string]> = [];
    for (const n of background) {
        if (n.kind !== 'account') continue;
        const nearest = [...merchants].sort(
            (p, q) => Math.hypot(p.x - n.x, p.y - n.y) - Math.hypot(q.x - n.x, q.y - n.y),
        );
        pairs.push([n.id, nearest[0].id]);
        if (Number(n.id.slice(1)) % 3 === 0 && nearest[1]) pairs.push([n.id, nearest[1].id]);
    }
    for (const a of ['a1', 'a2', 'a3', 'a4', 'a5']) {
        const nearest = [...merchants].sort(
            (p, q) => Math.hypot(p.x - byId.get(a)!.x, p.y - byId.get(a)!.y) - Math.hypot(q.x - byId.get(a)!.x, q.y - byId.get(a)!.y),
        );
        pairs.push([a, nearest[0].id]);
    }
    return pairs;
})();

// Identity links: only visible through the lens.
const ringLinks: Array<[string, string]> = [
    ['a1', 'd1'],
    ['a4', 'd1'],
    ['a5', 'd1'],
    ['a2', 'd2'],
    ['a3', 'd2'],
    ['a1', 'm1'],
    ['a2', 'm1'],
    ['a3', 'm1'],
    ['a4', 'm1'],
    ['a5', 'm1'],
];
const noiseLinks: Array<[string, string]> = [
    ['b1', 'b4'],
    ['b9', 'b12'],
    ['b17', 'b20'],
];

const linkName = ([a, b]: [string, string]) => `${byId.get(a)?.label} and ${byId.get(b)?.label}`;

function NodeMark({ node, bright }: { node: GraphNode; bright?: boolean }) {
    const fill = bright ? '#0c0c0e' : '#18181b';
    const stroke = bright ? (node.ring ? '#ececef' : 'rgba(236,236,239,0.6)') : 'rgba(255,255,255,0.28)';
    const r = node.ring ? 7 : 5;
    if (node.kind === 'device') {
        return <rect x={node.x - r} y={node.y - r} width={r * 2} height={r * 2} rx={2} fill={fill} stroke={stroke} strokeWidth={1.4} />;
    }
    if (node.kind === 'merchant') {
        return (
            <rect
                x={node.x - r}
                y={node.y - r}
                width={r * 2}
                height={r * 2}
                fill={fill}
                stroke={stroke}
                strokeWidth={1.4}
                transform={`rotate(45 ${node.x} ${node.y})`}
            />
        );
    }
    return <circle cx={node.x} cy={node.y} r={r} fill={fill} stroke={stroke} strokeWidth={1.4} />;
}

export function InvestigationLens() {
    const uid = useId().replace(/:/g, '');
    const svgRef = useRef<SVGSVGElement>(null);
    const clipRef = useRef<SVGCircleElement>(null);
    const loupeRef = useRef<SVGGElement>(null);
    const [found, setFound] = useState<string[]>([]);
    const foundRef = useRef(new Set<string>());

    useEffect(() => {
        const svg = svgRef.current;
        if (!svg) return;
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        const pos = { x: 140, y: 120 };
        const target = { x: 140, y: 120 };
        let pointerActive = false;
        let idleTimer = 0;
        let raf = 0;
        const start = performance.now();

        const place = () => {
            clipRef.current?.setAttribute('cx', String(pos.x));
            clipRef.current?.setAttribute('cy', String(pos.y));
            loupeRef.current?.setAttribute('transform', `translate(${pos.x} ${pos.y})`);
        };

        const discover = () => {
            let changed = false;
            ringLinks.forEach((link, index) => {
                const key = String(index);
                if (foundRef.current.has(key)) return;
                const a = byId.get(link[0])!;
                const b = byId.get(link[1])!;
                const mx = (a.x + b.x) / 2;
                const my = (a.y + b.y) / 2;
                if (Math.hypot(mx - pos.x, my - pos.y) < LENS_R * 0.62) {
                    foundRef.current.add(key);
                    changed = true;
                }
            });
            if (changed) setFound(Array.from(foundRef.current));
        };

        if (reduce) {
            // No drift: park the lens on the ring and show every link at once.
            pos.x = 320;
            pos.y = 236;
            place();
            ringLinks.forEach((_, i) => foundRef.current.add(String(i)));
            const frame = requestAnimationFrame(() => setFound(Array.from(foundRef.current)));
            return () => cancelAnimationFrame(frame);
        }

        const tick = (now: number) => {
            if (!pointerActive) {
                // Idle path: a slow figure that keeps returning across the ring.
                const t = (now - start) / 1000;
                target.x = 320 + 190 * Math.sin(t * 0.42);
                target.y = 232 + 120 * Math.sin(t * 0.73 + 0.6);
            }
            pos.x += (target.x - pos.x) * 0.075;
            pos.y += (target.y - pos.y) * 0.075;
            place();
            discover();
            raf = requestAnimationFrame(tick);
        };

        const toLocal = (event: PointerEvent) => {
            const rect = svg.getBoundingClientRect();
            return {
                x: ((event.clientX - rect.left) / rect.width) * W,
                y: ((event.clientY - rect.top) / rect.height) * H,
            };
        };

        const onMove = (event: PointerEvent) => {
            const p = toLocal(event);
            target.x = Math.max(LENS_R * 0.5, Math.min(W - LENS_R * 0.5, p.x));
            target.y = Math.max(LENS_R * 0.5, Math.min(H - LENS_R * 0.5, p.y));
            pointerActive = true;
            window.clearTimeout(idleTimer);
        };

        const onLeave = () => {
            window.clearTimeout(idleTimer);
            idleTimer = window.setTimeout(() => {
                pointerActive = false;
            }, 1400);
        };

        // Pause when the board is off screen.
        const observer = new IntersectionObserver(([entry]) => {
            cancelAnimationFrame(raf);
            if (entry.isIntersecting) raf = requestAnimationFrame(tick);
        });
        observer.observe(svg);
        svg.addEventListener('pointermove', onMove);
        svg.addEventListener('pointerdown', onMove);
        svg.addEventListener('pointerleave', onLeave);
        return () => {
            observer.disconnect();
            cancelAnimationFrame(raf);
            window.clearTimeout(idleTimer);
            svg.removeEventListener('pointermove', onMove);
            svg.removeEventListener('pointerdown', onMove);
            svg.removeEventListener('pointerleave', onLeave);
        };
    }, []);

    const foundSet = new Set(found);
    const total = ringLinks.length;
    const flagged = found.length === total;
    const latest = found.length ? ringLinks[Number(found[found.length - 1])] : null;

    return (
        <figure className="gx-lens" aria-label="Interactive illustration: a lens reveals hidden links between accounts">
            <div className="gx-lens__inner">
                <p className="gx-lens__hint">Move across the board to look closer</p>
                <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={`${uid}-t ${uid}-d`}>
                    <title id={`${uid}-t`}>A payment network with a hidden fraud ring</title>
                    <desc id={`${uid}-d`}>
                        Five accounts look unrelated in their payments. Inside the lens, links appear: they share two phones and
                        all top up the same merchant.
                    </desc>
                    <defs>
                        <clipPath id={`${uid}-clip`}>
                            <circle ref={clipRef} cx={140} cy={120} r={LENS_R} />
                        </clipPath>
                        <radialGradient id={`${uid}-glass`}>
                            <stop offset="0.6" stopColor="#ffffff" stopOpacity="0" />
                            <stop offset="1" stopColor="#ffffff" stopOpacity="0.09" />
                        </radialGradient>
                        <pattern id={`${uid}-grid`} width="16" height="16" patternUnits="userSpaceOnUse">
                            <path d="M16 0H0V16" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                        </pattern>
                    </defs>

                    {/* Base layer: what the bank sees by default. */}
                    <g aria-hidden="true">
                        {payments.map(([a, b]) => (
                            <line key={`p-${a}-${b}`} className="gx-edge" x1={byId.get(a)!.x} y1={byId.get(a)!.y} x2={byId.get(b)!.x} y2={byId.get(b)!.y} />
                        ))}
                        {ringLinks.map((link, i) => (
                            <line
                                key={`f-${i}`}
                                className="gx-found-edge"
                                data-found={foundSet.has(String(i))}
                                x1={byId.get(link[0])!.x}
                                y1={byId.get(link[0])!.y}
                                x2={byId.get(link[1])!.x}
                                y2={byId.get(link[1])!.y}
                            />
                        ))}
                        {nodes.map((n) => (
                            <NodeMark key={n.id} node={n} />
                        ))}
                    </g>

                    {/* Lens layer: identity links and labels, clipped to the loupe. */}
                    <g clipPath={`url(#${uid}-clip)`} aria-hidden="true">
                        <rect width={W} height={H} fill="#0a0a0c" />
                        <rect width={W} height={H} fill={`url(#${uid}-grid)`} />
                        {payments.map(([a, b]) => (
                            <line
                                key={`lp-${a}-${b}`}
                                stroke="rgba(255,255,255,0.16)"
                                x1={byId.get(a)!.x}
                                y1={byId.get(a)!.y}
                                x2={byId.get(b)!.x}
                                y2={byId.get(b)!.y}
                            />
                        ))}
                        {noiseLinks.map(([a, b]) =>
                            byId.get(a) && byId.get(b) ? (
                                <line key={`n-${a}-${b}`} className="gx-hidden-edge" x1={byId.get(a)!.x} y1={byId.get(a)!.y} x2={byId.get(b)!.x} y2={byId.get(b)!.y} />
                            ) : null,
                        )}
                        {ringLinks.map((link, i) => (
                            <line
                                key={`h-${i}`}
                                className="gx-hidden-edge"
                                data-ring="true"
                                x1={byId.get(link[0])!.x}
                                y1={byId.get(link[0])!.y}
                                x2={byId.get(link[1])!.x}
                                y2={byId.get(link[1])!.y}
                            />
                        ))}
                        {nodes.map((n) => (
                            <NodeMark key={`l-${n.id}`} node={n} bright />
                        ))}
                        {ringNodes.map((n) => (
                            <text key={`t-${n.id}`} className="gx-label" x={n.x + 12} y={n.y - 10}>
                                {n.label}
                            </text>
                        ))}
                    </g>

                    {/* The loupe itself. */}
                    <g ref={loupeRef} transform="translate(140 120)" aria-hidden="true" style={{ pointerEvents: 'none' }}>
                        <circle r={LENS_R} fill={`url(#${uid}-glass)`} stroke="rgba(255,255,255,0.55)" strokeWidth="1.5" />
                        <circle r={LENS_R + 6} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="10" />
                        {Array.from({ length: 24 }).map((_, i) => {
                            const angle = (i / 24) * Math.PI * 2;
                            const inner = LENS_R + (i % 6 === 0 ? 2 : 4);
                            const outer = LENS_R + 10;
                            return (
                                <line
                                    key={i}
                                    x1={Math.cos(angle) * inner}
                                    y1={Math.sin(angle) * inner}
                                    x2={Math.cos(angle) * outer}
                                    y2={Math.sin(angle) * outer}
                                    stroke="rgba(255,255,255,0.35)"
                                    strokeWidth="1"
                                />
                            );
                        })}
                        <line x1={-8} y1={0} x2={8} y2={0} stroke="rgba(255,255,255,0.4)" />
                        <line x1={0} y1={-8} x2={0} y2={8} stroke="rgba(255,255,255,0.4)" />
                    </g>
                </svg>
                <div className="gx-readout" aria-live="polite">
                    <div className="gx-readout__count">
                        {found.length}
                        <small>/{total}</small>
                    </div>
                    <p className="gx-readout__label">
                        <strong>Hidden links found</strong>
                        {latest ? `Latest: ${linkName(latest)}` : 'Payments alone look ordinary.'}
                    </p>
                    <span className="gx-status" data-flagged={flagged}>
                        <i aria-hidden="true" />
                        {flagged ? 'Ring flagged for review' : 'Looking'}
                    </span>
                    <div className="gx-readout__bar" aria-hidden="true">
                        <span style={{ ['--gx-progress' as string]: `${(found.length / total) * 100}%` }} />
                    </div>
                </div>
            </div>
        </figure>
    );
}
