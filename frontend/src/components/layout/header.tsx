'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState, useEffect } from 'react';
import { Menu, X, Github, Shield, Play } from 'lucide-react';

const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/architecture', label: 'Architecture' },
    { href: '/stack', label: 'Tech Stack' },
    { href: '/demo', label: 'Live Demo', highlight: true },
];

export function Header() {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const pathname = usePathname();

    // Scroll listener to toggle glassmorphism effect
    useEffect(() => {
        const handleScroll = () => {
            setScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header
            className={`fixed top-4 left-0 right-0 z-50 flex justify-center px-4 transition-all duration-300`}
        >
            <div
                className={`w-full max-w-6xl transition-all duration-300 rounded-2xl ${scrolled
                    ? 'bg-zinc-950/90 backdrop-blur-xl border border-white/5 shadow-2xl shadow-black/20 py-1'
                    : 'bg-transparent py-2 backdrop-blur-none'
                    }`}
            >
                <div className="px-6 flex items-center justify-between h-14">
                    {/* Logo Section */}
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-zinc-200 to-zinc-400 flex items-center justify-center shadow-lg shadow-white/5 group-hover:shadow-white/20 group-hover:scale-105 transition-all border border-white/10">
                            <Shield className="w-5 h-5 text-zinc-950" />
                        </div>
                        <div className="flex flex-col">
                            <span className="text-lg font-bold bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
                                GraphGuard
                            </span>
                        </div>
                    </Link>

                    {/* Desktop Navigation */}
                    <nav className="hidden md:flex items-center gap-1">
                        {navLinks.map((link) => {
                            const isActive = pathname === link.href;

                            // Highlighted 'Call to Action' button style
                            if (link.highlight) {
                                return (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        className="ml-2 flex items-center gap-2 px-5 py-2 text-sm font-medium bg-gradient-to-r from-zinc-100 to-zinc-400 text-zinc-950 rounded-full hover:from-white hover:to-zinc-300 transition-all shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02]"
                                    >
                                        <Play className="w-3 h-3 fill-current" />
                                        {link.label}
                                    </Link>
                                );
                            }

                            // Standard Nav Link style
                            return (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    className={`px-4 py-2 text-sm transition-all rounded-full hover:bg-zinc-800/50 ${isActive
                                        ? 'text-zinc-100 font-medium'
                                        : 'text-zinc-400 hover:text-zinc-200'
                                        }`}
                                >
                                    {link.label}
                                </Link>
                            );
                        })}
                    </nav>

                    {/* Desktop Actions (Socials) */}
                    <div className="hidden md:flex items-center gap-3">
                        <a
                            href="https://github.com"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 px-3 py-2 text-sm text-zinc-400 hover:text-zinc-100 transition-colors rounded-full hover:bg-zinc-800/50"
                        >
                            <Github className="w-4 h-4" />
                            <span>GitHub</span>
                        </a>
                    </div>

                    {/* Mobile Menu Toggle */}
                    <button
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        className="md:hidden p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-lg transition-colors"
                    >
                        {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </button>
                </div>

                {/* Mobile Dropdown Menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden px-4 pb-4 pt-2 border-t border-zinc-800">
                        <nav className="flex flex-col gap-1">
                            {navLinks.map((link) => (
                                <Link
                                    key={link.href}
                                    href={link.href}
                                    onClick={() => setMobileMenuOpen(false)}
                                    className={`px-4 py-3 text-sm rounded-lg transition-colors ${pathname === link.href
                                        ? 'text-zinc-100 bg-zinc-800'
                                        : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50'
                                        }`}
                                >
                                    {link.label}
                                </Link>
                            ))}
                            <a
                                href="https://github.com"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-2 px-4 py-3 text-sm text-zinc-400 hover:text-zinc-100"
                            >
                                <Github className="w-4 h-4" />
                                GitHub
                            </a>
                        </nav>
                    </div>
                )}
            </div>
        </header>
    );
}
