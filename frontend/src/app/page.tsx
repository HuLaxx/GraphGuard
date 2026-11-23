import Link from 'next/link';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import { RingGraph } from '@/components/casefile/ring-graph';

const trail = [
    {
        title: 'Ingest',
        text: 'Payments arrive on Kafka with Avro schemas. Delivery is at-least-once, and the consumer picks up where it stopped after a restart.',
        tech: 'Kafka, Avro schema registry',
    },
    {
        title: 'Connect',
        text: 'Each payment links an account, a device and a merchant in Neo4j. Features are computed as of the payment time, so the model never sees the future.',
        tech: 'Neo4j, point-in-time features',
    },
    {
        title: 'Score',
        text: 'An XGBoost model scores the payment. A new model replaces the current one only if it clears the release gate.',
        tech: 'XGBoost, MLflow model registry',
    },
    {
        title: 'Explain',
        text: 'SHAP values show which features pushed each score up or down, so the reason travels with the decision.',
        tech: 'SHAP',
    },
    {
        title: 'Decide',
        text: 'An analyst opens a signed case, checks the evidence and records the outcome. The review flow is tested in a real browser.',
        tech: 'FastAPI, GraphQL, Next.js',
    },
];

const proof = [
    {
        claim: 'Model release gate',
        evidence: (
            <>
                The clean model was promoted with PR-AUC <span className="gg-num">0.765</span> and ROC-AUC{' '}
                <span className="gg-num">0.941</span>. A model trained on shuffled labels scored PR-AUC{' '}
                <span className="gg-num">0.138</span> and was rejected; the champion stayed put.
            </>
        ),
    },
    {
        claim: 'Kafka to Neo4j',
        evidence: 'Events travel through a real Kafka broker into a real Neo4j database, including consumer restarts.',
    },
    {
        claim: 'Calibration and drift',
        evidence: (
            <>
                Expected calibration error <span className="gg-num">0.063</span> on the held-out period, and a drift suite
                that flags shifted feature distributions.
            </>
        ),
    },
    {
        claim: 'Explanations',
        evidence: 'SHAP values are produced for each case, with their latency measured at p50 and p95.',
    },
    {
        claim: 'Analyst review',
        evidence: 'A signed case is opened, reviewed and recorded in real Chromium.',
    },
];

export default function HomePage() {
    return (
        <>
            <Header />
            <main>
                <section className="gg-hero">
                    <div className="gg-wrap gg-hero__grid">
                        <div>
                            <h1 className="gg-hero__title">Fraud hides in the connections between accounts.</h1>
                            <p className="gg-hero__lede">
                                GraphGuard follows payments into a graph of accounts, devices and merchants, scores each one with
                                an explainable model, and hands the analyst a case they can check line by line.
                            </p>
                            <div className="gg-hero__actions">
                                <Link href="/cases" className="gg-button gg-button--primary">
                                    Open the case desk
                                </Link>
                                <a href="#trail" className="gg-button gg-button--quiet">
                                    See how a case is built
                                </a>
                            </div>
                            <p className="gg-hero__scope">
                                A portfolio project by Rahul Khanke. The results on this page come from CI runs on synthetic
                                data; no real bank data is used.
                            </p>
                        </div>
                        <figure className="gg-board">
                            <div className="gg-board__canvas">
                                <RingGraph />
                                <div className="gg-note">
                                <p>
                                    Five accounts, two phones, one merchant. All five topped up the same card within the hour,
                                    from <strong>phones they share</strong>.
                                </p>
                                <p>Flagged for review. Shared devices drove most of the risk.</p>
                                <p className="gg-note__sig">Investigator&apos;s note, illustrative case</p>
                                </div>
                            </div>
                            <figcaption>
                                <span className="gg-legend">
                                    <span><i className="is-account" /> Account</span>
                                    <span><i /> Device</span>
                                    <span><i className="is-merchant" /> Merchant</span>
                                    <span><i className="is-flag" /> Flagged link</span>
                                </span>
                            </figcaption>
                        </figure>
                    </div>
                </section>

                <section className="gg-section" id="trail" aria-labelledby="trail-title">
                    <div className="gg-wrap">
                        <div className="gg-section__head">
                            <h2 className="gg-h2" id="trail-title">From a payment to a decision in five steps</h2>
                            <p className="gg-section__intro">
                                Each stage runs in CI against real services, so the claims further down are checked on every
                                change to the code.
                            </p>
                        </div>
                        <ol className="gg-trail">
                            {trail.map((stage) => (
                                <li key={stage.title}>
                                    <h3>{stage.title}</h3>
                                    <p>{stage.text}</p>
                                    <p className="gg-trail__tech">{stage.tech}</p>
                                </li>
                            ))}
                        </ol>
                    </div>
                </section>

                <section className="gg-section" aria-labelledby="proof-title">
                    <div className="gg-wrap">
                        <div className="gg-section__head">
                            <h2 className="gg-h2" id="proof-title">What has been checked</h2>
                            <p className="gg-section__intro">
                                Synthetic data throughout. These results describe how the pipeline behaves, not how well it
                                would catch real fraud.
                            </p>
                        </div>
                        <table className="gg-ledger">
                            <caption>Source: GitHub Actions runs on the main branch, November 2026.</caption>
                            <thead>
                                <tr>
                                    <th scope="col">Claim</th>
                                    <th scope="col">Evidence</th>
                                    <th scope="col">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {proof.map((row) => (
                                    <tr key={row.claim}>
                                        <th scope="row">{row.claim}</th>
                                        <td>{row.evidence}</td>
                                        <td>Passing in CI</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                <section className="gg-section" aria-labelledby="limits-title">
                    <div className="gg-wrap gg-limits">
                        <div>
                            <h2 className="gg-h2" id="limits-title">What this is not</h2>
                            <div className="gg-next">
                                <Link href="/architecture" className="gg-button gg-button--quiet">
                                    Read the architecture
                                </Link>
                                <a href="https://github.com/HuLaxx/GraphGuard" className="gg-button gg-button--quiet">
                                    View the code
                                </a>
                            </div>
                        </div>
                        <ul>
                            <li>
                                It is not trained on real bank data. The transactions come from a seeded generator, and the
                                scores describe that generator.
                            </li>
                            <li>The graph neural network (GAT) path is experimental and is not used for scoring.</li>
                            <li>
                                The hosted site is the front end only. Kafka, Neo4j and the model service run locally with
                                Docker Compose.
                            </li>
                        </ul>
                    </div>
                </section>
            </main>
            <Footer />
        </>
    );
}
