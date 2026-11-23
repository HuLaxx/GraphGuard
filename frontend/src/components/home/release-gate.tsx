'use client';

import { useEffect, useRef, useState } from 'react';

/*
 * Release gate visual. Values come from the registry CI run on synthetic data
 * (ml/registry/release_policy.json and docs/EVIDENCE_REGISTER.md).
 */
const FLOOR = 0.7;

const models = [
    { name: 'Clean model', note: 'Promoted to champion', value: 0.765, pass: true },
    { name: 'Shuffled-label model', note: 'Rejected, champion kept', value: 0.138, pass: false },
];

export function ReleaseGate() {
    const ref = useRef<HTMLDivElement>(null);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setVisible(true);
                    observer.disconnect();
                }
            },
            { threshold: 0.35 },
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, []);

    return (
        <div className="gx-gate" ref={ref} data-visible={visible}>
            <figure style={{ margin: 0 }}>
                <div className="gx-gate__chart" role="img" aria-label="PR-AUC on the synthetic test split: clean model 0.765 clears the 0.70 floor; shuffled-label model 0.138 does not.">
                    <div className="gx-gate__line" style={{ ['--gx-floor' as string]: FLOOR }}>
                        <span>Release floor, PR-AUC 0.70</span>
                    </div>
                    {models.map((m, i) => (
                        <div
                            className="gx-column"
                            key={m.name}
                            data-pass={m.pass}
                            style={{ ['--gx-value' as string]: m.value, ['--gx-i' as string]: `${i * 220}ms` }}
                        >
                            <div className="gx-column__value">{m.value.toFixed(3)}</div>
                            <div className="gx-column__bar" />
                        </div>
                    ))}
                </div>
                <figcaption className="gx-gate__names">
                    {models.map((m) => (
                        <span key={m.name}>
                            <strong>{m.name}</strong>
                            {m.note}
                        </span>
                    ))}
                </figcaption>
            </figure>
            <div>
                <dl className="gx-facts">
                    <div>
                        <dt>ROC-AUC, clean model</dt>
                        <dd>
                            0.941<small>floor 0.90</small>
                        </dd>
                    </div>
                    <div>
                        <dt>Calibration error (ECE)</dt>
                        <dd>
                            0.063<small>ceiling 0.10</small>
                        </dd>
                    </div>
                    <div>
                        <dt>Recall at the validation threshold</dt>
                        <dd>
                            0.81<small>floor 0.75</small>
                        </dd>
                    </div>
                </dl>
                <p className="gx-source">Synthetic test split, 144 rows. Re-run on every change by GitHub Actions.</p>
            </div>
        </div>
    );
}
