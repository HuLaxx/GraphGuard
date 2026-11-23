/**
 * Illustrative synthetic fraud ring: five accounts share two devices and all pay one
 * merchant. Flagged edges are marked with a highlighter stroke. No model output is shown.
 */
type Node = {
    id: string;
    x: number;
    y: number;
    kind: 'account' | 'device' | 'merchant';
    label: string;
    ring?: boolean;
    lx?: number;
    ly?: number;
    anchor?: 'start' | 'middle' | 'end';
};

const nodes: Node[] = [
    { id: 'a1', x: 150, y: 120, kind: 'account', label: 'acct 4417', ring: true, lx: -18, ly: -16, anchor: 'end' },
    { id: 'a2', x: 104, y: 278, kind: 'account', label: 'acct 0932', ring: true, lx: 0, ly: -22, anchor: 'middle' },
    { id: 'a3', x: 262, y: 420, kind: 'account', label: 'acct 7710', ring: true, lx: 0, ly: 34, anchor: 'middle' },
    { id: 'a4', x: 360, y: 188, kind: 'account', label: 'acct 2268', ring: true, lx: 16, ly: -16, anchor: 'start' },
    { id: 'a5', x: 250, y: 290, kind: 'account', label: 'acct 5091', ring: true, lx: -18, ly: 30, anchor: 'end' },
    { id: 'd1', x: 268, y: 84, kind: 'device', label: 'phone d-09', ring: true, lx: 20, ly: 5, anchor: 'start' },
    { id: 'd2', x: 112, y: 420, kind: 'device', label: 'phone d-31', ring: true, lx: 0, ly: 36, anchor: 'middle' },
    { id: 'm1', x: 500, y: 250, kind: 'merchant', label: 'top-up merchant', ring: true, lx: 0, ly: -26, anchor: 'middle' },
    { id: 'b1', x: 470, y: 70, kind: 'account', label: '' },
    { id: 'b2', x: 640, y: 112, kind: 'account', label: '' },
    { id: 'b3', x: 664, y: 300, kind: 'account', label: '' },
    { id: 'b4', x: 520, y: 470, kind: 'account', label: '' },
    { id: 'b5', x: 650, y: 470, kind: 'device', label: '' },
    { id: 'm2', x: 620, y: 210, kind: 'merchant', label: '' },
    { id: 'b6', x: 420, y: 380, kind: 'account', label: '' },
];

const ringEdges: Array<[string, string]> = [
    ['a1', 'd1'], ['a4', 'd1'], ['a5', 'd1'],
    ['a2', 'd2'], ['a3', 'd2'], ['a5', 'd2'],
    ['a1', 'm1'], ['a2', 'm1'], ['a3', 'm1'], ['a4', 'm1'], ['a5', 'm1'],
];

const ordinaryEdges: Array<[string, string]> = [
    ['b1', 'm1'], ['b2', 'm2'], ['b3', 'm2'], ['b3', 'b5'], ['b4', 'b5'],
    ['b6', 'm1'], ['b2', 'm1'], ['b6', 'b4'], ['b1', 'm2'],
];

const at = (id: string) => nodes.find((n) => n.id === id)!;

function Shape({ node }: { node: Node }) {
    const stroke = node.ring ? '#eceff8' : '#46527f';
    const fill = '#121933';
    if (node.kind === 'device') {
        return <rect x={node.x - 10} y={node.y - 10} width={20} height={20} fill={fill} stroke={stroke} strokeWidth={2.5} />;
    }
    if (node.kind === 'merchant') {
        return <rect x={node.x - 12} y={node.y - 12} width={24} height={24} fill={fill} stroke={stroke} strokeWidth={2.5} transform={`rotate(45 ${node.x} ${node.y})`} />;
    }
    return <circle cx={node.x} cy={node.y} r={node.ring ? 11 : 8} fill={fill} stroke={stroke} strokeWidth={2.5} />;
}

export function RingGraph() {
    return (
        <svg viewBox="0 0 720 520" role="img" aria-labelledby="gg-ring-title gg-ring-desc">
            <title id="gg-ring-title">An illustrative fraud ring</title>
            <desc id="gg-ring-desc">
                Five accounts share two phones and all pay the same top-up merchant. The links between them are highlighted;
                other accounts and merchants are shown faintly for contrast.
            </desc>
            <defs>
                <pattern id="gg-ledger" width="720" height="36" patternUnits="userSpaceOnUse">
                    <path d="M0 35.5 H720" stroke="#232d55" strokeWidth="1" />
                </pattern>
            </defs>
            <rect width="720" height="520" fill="url(#gg-ledger)" />
            <path d="M58 0 V520" stroke="#3a2a4f" strokeWidth="1.5" />

            <g stroke="#2c3763" strokeWidth="1.5">
                {ordinaryEdges.map(([a, b]) => (
                    <line key={`${a}${b}`} x1={at(a).x} y1={at(a).y} x2={at(b).x} y2={at(b).y} />
                ))}
            </g>

            <g stroke="#f5d547" strokeOpacity="0.32" strokeWidth="14" strokeLinecap="round" fill="none">
                {ringEdges.map(([a, b]) => (
                    <path key={`h${a}${b}`} className="gg-ring-path" pathLength={1} d={`M${at(a).x} ${at(a).y} L${at(b).x} ${at(b).y}`} />
                ))}
            </g>
            <g stroke="#f5d547" strokeWidth="2" fill="none">
                {ringEdges.map(([a, b]) => (
                    <path key={`l${a}${b}`} className="gg-ring-path" pathLength={1} d={`M${at(a).x} ${at(a).y} L${at(b).x} ${at(b).y}`} />
                ))}
            </g>

            {nodes.map((node) => (
                <g key={node.id}>
                    <Shape node={node} />
                    {node.label && (
                        <text
                            x={node.x + (node.lx ?? 18)}
                            y={node.y + (node.ly ?? 5)}
                            textAnchor={node.anchor ?? 'start'}
                            fill="#d9deee"
                            fontSize="15"
                            fontFamily="var(--font-archivo), Archivo, sans-serif"
                            paintOrder="stroke"
                            stroke="#121933"
                            strokeWidth="5"
                            strokeLinejoin="round"
                        >
                            {node.label}
                        </text>
                    )}
                </g>
            ))}
        </svg>
    );
}

export function Wordmark() {
    return (
        <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
            <path d="M6 7 L19 6 L13 20 Z" fill="none" stroke="#f5d547" strokeOpacity="0.45" strokeWidth="5" strokeLinejoin="round" />
            <path d="M6 7 L19 6 L13 20 Z" fill="none" stroke="#eceff8" strokeWidth="1.6" strokeLinejoin="round" />
            <circle cx="6" cy="7" r="3" fill="#0b1020" stroke="#eceff8" strokeWidth="1.6" />
            <rect x="16.5" y="3.5" width="5" height="5" fill="#0b1020" stroke="#eceff8" strokeWidth="1.6" />
            <rect x="10.5" y="17.5" width="5" height="5" fill="#0b1020" stroke="#eceff8" strokeWidth="1.6" transform="rotate(45 13 20)" />
        </svg>
    );
}
