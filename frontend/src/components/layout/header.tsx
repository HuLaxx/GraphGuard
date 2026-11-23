'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Wordmark } from '@/components/casefile/ring-graph';

const navLinks = [
    { href: '/cases', label: 'Case desk' },
    { href: '/architecture', label: 'Architecture' },
    { href: '/stack', label: 'Stack' },
    { href: '/demo', label: 'GraphQL demo' },
] as const;

export function Header() {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    return (
        <header className="gg-header">
            <div className="gg-wrap">
                <div className="gg-header__bar">
                    <Link href="/" className="gg-wordmark" aria-label="GraphGuard home">
                        <Wordmark />
                        GraphGuard
                    </Link>
                    <nav className="gg-nav" aria-label="Main">
                        {navLinks.map((link) => (
                            <Link key={link.href} href={link.href} aria-current={pathname === link.href ? 'page' : undefined}>
                                {link.label}
                            </Link>
                        ))}
                    </nav>
                    <a className="gg-header__repo" href="https://github.com/HuLaxx/GraphGuard">
                        Code on GitHub
                    </a>
                    <button
                        type="button"
                        className="gg-menu-button"
                        aria-expanded={open}
                        aria-controls="gg-mobile-nav"
                        onClick={() => setOpen((value) => !value)}
                    >
                        {open ? 'Close' : 'Menu'}
                    </button>
                </div>
                <nav id="gg-mobile-nav" className="gg-mobile-nav" data-open={open} aria-label="Main">
                    {navLinks.map((link) => (
                        <Link key={link.href} href={link.href} onClick={() => setOpen(false)}>
                            {link.label}
                        </Link>
                    ))}
                    <a href="https://github.com/HuLaxx/GraphGuard">Code on GitHub</a>
                </nav>
            </div>
        </header>
    );
}
