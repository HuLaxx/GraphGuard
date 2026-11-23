import Link from 'next/link';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';
import { InvestigationLens } from '@/components/home/investigation-lens';
import { PaymentStory } from '@/components/home/payment-story';
import { ReleaseGate } from '@/components/home/release-gate';
import './home.css';

const delay = (ms: number) => ({ ['--gx-delay' as string]: `${ms}ms` });

export default function HomePage() {
    return (
        <div className="min-h-screen bg-transparent">
            <Header />
            <main className="gx">
                <section className="gx-hero">
                    <div className="gx-wrap gx-hero__grid">
                        <div>
                            <h1 className="gx-hero__title gx-metal gx-rise" style={delay(0)}>
                                Fraud never travels alone.
                            </h1>
                            <p className="gx-hero__lede gx-rise" style={delay(140)}>
                                Each payment in a ring looks ordinary on its own. GraphGuard follows them into a graph of
                                accounts, phones and merchants, scores them with a model that has to earn its release, and hands an
                                analyst a case they can check line by line.
                            </p>
                            <div className="gx-hero__actions gx-rise" style={delay(260)}>
                                <Link href="/cases" className="gx-button gx-button--primary">
                                    Open the case desk
                                </Link>
                                <a href="#story" className="gx-button gx-button--ghost">
                                    Follow one payment
                                </a>
                            </div>
                            <p className="gx-hero__scope gx-rise" style={delay(380)}>
                                Synthetic data throughout. Every result on this page comes from CI runs against real Kafka, Neo4j
                                and MLflow services.
                            </p>
                        </div>
                        <div className="gx-rise" style={delay(200)}>
                            <InvestigationLens />
                        </div>
                    </div>
                </section>

                <section className="gx-section" id="story" aria-labelledby="story-title">
                    <div className="gx-wrap">
                        <h2 className="gx-h2 gx-metal" id="story-title">
                            Follow one payment from card to case.
                        </h2>
                        <p className="gx-intro">
                            Five stages, each running against real services in CI. Scroll to watch an illustrative payment move
                            through them.
                        </p>
                        <PaymentStory />
                    </div>
                </section>

                <section className="gx-section" aria-labelledby="gate-title">
                    <div className="gx-wrap">
                        <h2 className="gx-h2 gx-metal" id="gate-title">
                            A model has to earn its release.
                        </h2>
                        <p className="gx-intro">
                            Every candidate is scored on a held-out period and must clear fixed floors before it replaces the
                            champion. To prove the gate bites, CI also trains a model on shuffled labels and expects it to be
                            turned away.
                        </p>
                        <ReleaseGate />
                    </div>
                </section>

                <section className="gx-section" aria-labelledby="limits-title">
                    <div className="gx-wrap gx-close">
                        <div>
                            <h2 className="gx-h2 gx-metal" id="limits-title">
                                What it is, and what it isn&apos;t.
                            </h2>
                            <p className="gx-intro">
                                The numbers describe a seeded generator, not a bank. Read the architecture or the code to see
                                exactly how each claim is checked.
                            </p>
                            <div className="gx-hero__actions">
                                <Link href="/architecture" className="gx-button gx-button--ghost">
                                    Read the architecture
                                </Link>
                                <a href="https://github.com/HuLaxx/GraphGuard" className="gx-button gx-button--ghost">
                                    View the code
                                </a>
                            </div>
                        </div>
                        <ul className="gx-limits">
                            <li>
                                <strong>Synthetic data only</strong>
                                Transactions come from a seeded generator, so scores describe that generator rather than real fraud.
                            </li>
                            <li>
                                <strong>The graph neural network is experimental</strong>
                                The GAT path trains, but scoring uses the XGBoost champion from the registry.
                            </li>
                            <li>
                                <strong>Heavy services run locally</strong>
                                The hosted site is the front end. Kafka, Neo4j and the model service run with Docker Compose.
                            </li>
                        </ul>
                    </div>
                </section>
            </main>
            <Footer />
        </div>
    );
}
