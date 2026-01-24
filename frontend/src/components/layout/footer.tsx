import Link from 'next/link';
import { Shield, Github, Linkedin, Twitter } from 'lucide-react';

const footerLinks = {
    product: [
        { label: 'Home', href: '/' },
        { label: 'Live Demo', href: '/demo' },
    ],
    resources: [
        { label: 'Architecture', href: '/architecture' },
        { label: 'Tech Stack', href: '/stack' },
    ],
    company: [
        { label: 'GitHub', href: 'https://github.com' },
    ],
};

const socialLinks = [
    { icon: Github, href: 'https://github.com', label: 'GitHub' },
    { icon: Linkedin, href: 'https://linkedin.com', label: 'LinkedIn' },
    { icon: Twitter, href: 'https://twitter.com', label: 'Twitter' },
];

export function Footer() {
    return (
        <footer className="bg-zinc-950 border-t border-zinc-800">
            <div className="max-w-7xl mx-auto px-6 py-20 pb-24">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12">
                    {/* Brand */}
                    <div className="lg:col-span-2">
                        <Link href="/" className="flex items-center gap-3 mb-4 group">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-zinc-200 to-zinc-400 flex items-center justify-center shadow-lg shadow-white/5 group-hover:shadow-white/20 group-hover:scale-105 transition-all">
                                <Shield className="w-5 h-5 text-zinc-950" />
                            </div>
                            <span className="text-xl font-bold text-zinc-100">
                                GraphGuard
                            </span>
                        </Link>
                        <p className="text-zinc-500 text-sm max-w-sm mb-6">
                            Enterprise-grade real-time fraud detection platform.
                            Graph analytics, ML ensemble models, and explainable AI.
                        </p>
                        <div className="flex gap-4">
                            {socialLinks.map((social) => (
                                <a
                                    key={social.label}
                                    href={social.href}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 hover:text-zinc-100 hover:border-zinc-500/50 transition-all"
                                    aria-label={social.label}
                                >
                                    <social.icon className="w-5 h-5" />
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* Links */}
                    <div>
                        <h3 className="text-sm font-semibold text-zinc-100 mb-4">Product</h3>
                        <ul className="space-y-3">
                            {footerLinks.product.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href as any}
                                        className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-zinc-100 mb-4">Resources</h3>
                        <ul className="space-y-3">
                            {footerLinks.resources.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href as any}
                                        className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div>
                        <h3 className="text-sm font-semibold text-zinc-100 mb-4">Company</h3>
                        <ul className="space-y-3">
                            {footerLinks.company.map((link) => (
                                <li key={link.label}>
                                    <Link
                                        href={link.href as any}
                                        className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
                                    >
                                        {link.label}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Bottom */}
                <div className="mt-16 pt-8 border-t border-zinc-900 flex flex-col md:flex-row items-center justify-between gap-4">
                    <p className="text-sm text-zinc-600">
                        © {new Date().getFullYear()} GraphGuard. Portfolio Project.
                    </p>
                    <div className="flex items-center gap-6 text-sm text-zinc-600">
                        <Link href={"#" as any} className="hover:text-zinc-400 transition-colors">Privacy</Link>
                        <Link href={"#" as any} className="hover:text-zinc-400 transition-colors">Terms</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
