'use client';

import { useEffect, useRef, useState } from 'react';

/*
 * Sticky scroll story: one illustrative payment travels through the five stages.
 * The stage on the left changes as each step on the right reaches the middle of
 * the viewport. Values in the scenes are illustrative and labelled as such.
 */

const steps = [
    {
        title: 'Ingest',
        text: 'The payment lands on Kafka as an Avro record checked against the schema registry. Delivery is at-least-once, and the consumer resumes where it stopped after a restart.',
        tech: 'Kafka, Avro schema registry',
    },
    {
        title: 'Connect',
        text: 'Neo4j links the account to its phone and the merchant. Features are taken as of the payment time, so the model never sees anything from the future.',
        tech: 'Neo4j, point-in-time features',
    },
    {
        title: 'Score',
        text: 'An XGBoost model scores the payment. It only got this job by clearing the release gate in the MLflow registry.',
        tech: 'XGBoost, MLflow registry',
    },
    {
        title: 'Explain',
        text: 'SHAP breaks the score into the features that pushed it up and the ones that pulled it down, and the explanation travels with the case.',
        tech: 'SHAP',
    },
    {
        title: 'Decide',
        text: 'An analyst opens the signed case, checks the evidence and records a decision. The model never makes the call on its own.',
        tech: 'FastAPI, GraphQL, Next.js',
    },
];

const shap = [
    { name: 'device_user_count', value: 0.31 },
    { name: 'merchant_fraud_rate', value: 0.18 },
    { name: 'txn_count_1h', value: 0.12 },
    { name: 'amount_zscore', value: 0.06 },
    { name: 'device_age_days', value: -0.09 },
];

function IngestScene() {
    const records = [
        { tx: 't-90319', amount: '£24.00', device: 'd-77' },
        { tx: 't-90320', amount: '£9.99', device: 'd-12' },
        { tx: 't-90321', amount: '£480.00', device: 'd-09' },
    ];
    return (
        <div className="gx-queue">
            {records.map((r) => (
                <div className="gx-record" key={r.tx}>
                    <dl>
                        <dt>payment</dt>
                        <dd>{r.tx}</dd>
                        <dt>amount</dt>
                        <dd>{r.amount}</dd>
                        <dt>device</dt>
                        <dd>{r.device}</dd>
                        <dt>schema</dt>
                        <dd>transaction v3</dd>
                    </dl>
                </div>
            ))}
        </div>
    );
}

function ConnectScene() {
    return (
        <svg viewBox="0 -24 360 284" width="100%" style={{ maxWidth: 420 }} aria-hidden="true">
            <line x1="70" y1="130" x2="180" y2="60" stroke="#ececef" strokeWidth="1.5" />
            <line x1="70" y1="130" x2="290" y2="140" stroke="#e8cf8f" strokeWidth="2" />
            <line x1="180" y1="60" x2="250" y2="36" stroke="rgba(236,236,239,0.5)" strokeDasharray="3 4" />
            <line x1="180" y1="60" x2="120" y2="22" stroke="rgba(236,236,239,0.5)" strokeDasharray="3 4" />
            <line x1="290" y1="140" x2="250" y2="220" stroke="rgba(255,255,255,0.15)" />
            <line x1="290" y1="140" x2="330" y2="214" stroke="rgba(255,255,255,0.15)" />
            <circle cx="70" cy="130" r="10" fill="#0c0c0e" stroke="#ececef" strokeWidth="1.6" />
            <rect x="171" y="51" width="18" height="18" rx="3" fill="#0c0c0e" stroke="#ececef" strokeWidth="1.6" />
            <rect x="281" y="131" width="18" height="18" fill="#0c0c0e" stroke="#e8cf8f" strokeWidth="1.6" transform="rotate(45 290 140)" />
            <circle cx="250" cy="36" r="6" fill="#0c0c0e" stroke="rgba(236,236,239,0.6)" />
            <circle cx="120" cy="22" r="6" fill="#0c0c0e" stroke="rgba(236,236,239,0.6)" />
            <circle cx="250" cy="220" r="5" fill="#0c0c0e" stroke="rgba(255,255,255,0.3)" />
            <circle cx="330" cy="214" r="5" fill="#0c0c0e" stroke="rgba(255,255,255,0.3)" />
            <text className="gx-label" x="40" y="160">acct 4417</text>
            <text className="gx-label" x="196" y="76">phone d-09</text>
            <text className="gx-label" x="250" y="172">top-up merchant</text>
            <text className="gx-label" x="214" y="18">2 more accounts</text>
        </svg>
    );
}

function ScoreScene() {
    const score = 0.91;
    return (
        <svg className="gx-gauge" viewBox="0 0 240 150" aria-hidden="true" style={{ ['--gx-score' as string]: score }}>
            <path d="M20 130 A100 100 0 0 1 220 130" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="10" strokeLinecap="round" />
            <path
                className="gx-gauge__arc"
                d="M20 130 A100 100 0 0 1 220 130"
                fill="none"
                stroke="#e8cf8f"
                strokeWidth="10"
                strokeLinecap="round"
                pathLength={1}
            />
            <text className="gx-gauge__value" x="120" y="128" textAnchor="middle">
                0.91
            </text>
        </svg>
    );
}

function ExplainScene() {
    const max = 0.35;
    return (
        <div className="gx-shap">
            {shap.map((f, i) => (
                <div className="gx-shap__row" key={f.name}>
                    <span>{f.name}</span>
                    <span className="gx-shap__track">
                        <span
                            className="gx-shap__bar"
                            data-dir={f.value >= 0 ? 'up' : 'down'}
                            style={{ width: `${(Math.abs(f.value) / max) * 50}%`, ['--gx-i' as string]: `${i * 90}ms` }}
                        />
                    </span>
                    <span className="gx-shap__value">
                        {f.value > 0 ? '+' : '−'}
                        {Math.abs(f.value).toFixed(2)}
                    </span>
                </div>
            ))}
        </div>
    );
}

function DecideScene() {
    return (
        <div className="gx-case">
            <h4>Case 4417-R</h4>
            <p>Five accounts, two shared phones, one top-up merchant. Shared devices drove most of the score.</p>
            <p>Decision: escalate to the fraud team. Signed by the reviewing analyst.</p>
            <svg className="gx-seal" viewBox="0 0 100 100" aria-hidden="true">
                <circle cx="50" cy="50" r="44" fill="rgba(232,207,143,0.08)" stroke="#e8cf8f" strokeWidth="1.5" />
                <circle cx="50" cy="50" r="36" fill="none" stroke="#e8cf8f" strokeWidth="0.8" strokeDasharray="2 3" />
                <path d="M34 51 L45 62 L67 38" fill="none" stroke="#e8cf8f" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        </div>
    );
}

const scenes = [IngestScene, ConnectScene, ScoreScene, ExplainScene, DecideScene];

export function PaymentStory() {
    const [active, setActive] = useState(0);
    const stepRefs = useRef<Array<HTMLLIElement | null>>([]);

    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) setActive(Number((entry.target as HTMLElement).dataset.index));
                }
            },
            // On narrow screens the sticky stage covers the top, so steps activate lower down.
            { rootMargin: window.matchMedia('(max-width: 980px)').matches ? '-46% 0px -50% 0px' : '-45% 0px -45% 0px' },
        );
        stepRefs.current.forEach((el) => el && observer.observe(el));
        return () => observer.disconnect();
    }, []);

    return (
        <div className="gx-story">
            <div className="gx-story__stage">
                <div className="gx-stage" aria-hidden="true">
                    {scenes.map((Scene, i) => (
                        <div className="gx-scene" data-active={active === i} key={steps[i].title}>
                            <p className="gx-scene__caption">Illustrative payment t-90321</p>
                            <Scene />
                        </div>
                    ))}
                    <div className="gx-stage__rail">
                        {steps.map((s, i) => (
                            <span key={s.title} data-done={i <= active} />
                        ))}
                    </div>
                </div>
            </div>
            <ol className="gx-steps">
                {steps.map((step, i) => (
                    <li
                        key={step.title}
                        className="gx-step"
                        data-index={i}
                        data-active={active === i}
                        ref={(el) => {
                            stepRefs.current[i] = el;
                        }}
                    >
                        <span className="gx-step__n">{i + 1}</span>
                        <h3>{step.title}</h3>
                        <p>{step.text}</p>
                        <small>{step.tech}</small>
                    </li>
                ))}
            </ol>
        </div>
    );
}
