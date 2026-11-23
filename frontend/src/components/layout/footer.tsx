import Link from 'next/link';
import { Wordmark } from '@/components/casefile/ring-graph';

export function Footer() {
    return (
        <footer className="gg-footer">
            <div className="gg-wrap gg-footer__grid">
                <div>
                    <Link href="/" className="gg-wordmark" aria-label="GraphGuard home">
                        <Wordmark />
                        GraphGuard
                    </Link>
                    <p>
                        A portfolio project by Rahul Khanke. All data is synthetic; nothing here describes a real bank or
                        customer.
                    </p>
                </div>
                <nav aria-label="Footer">
                    <Link href="/cases">Case desk</Link>
                    <Link href="/architecture">Architecture</Link>
                    <Link href="/stack">Stack</Link>
                    <Link href="/demo">GraphQL demo</Link>
                    <a href="https://github.com/HuLaxx/GraphGuard">GitHub</a>
                    <a href="https://portfolio.hulax.uk">Rahul&apos;s portfolio</a>
                </nav>
            </div>
        </footer>
    );
}
