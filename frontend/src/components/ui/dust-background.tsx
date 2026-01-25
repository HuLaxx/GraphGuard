"use client";

import { useEffect, useRef } from "react";

type DustParticle = {
    x: number;
    y: number;
    vx: number;
    vy: number;
    r: number;
    alpha: number;
    phase: number;
};

export function DustBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let width = 0;
        let height = 0;
        let dpr = Math.max(window.devicePixelRatio || 1, 1);
        let animationFrame = 0;
        let particles: DustParticle[] = [];

        const resize = () => {
            width = window.innerWidth;
            height = window.innerHeight;
            dpr = Math.max(window.devicePixelRatio || 1, 1);

            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            const count = Math.min(Math.floor((width * height) / 14000), 180);
            particles = Array.from({ length: count }, () => ({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.18,
                vy: (Math.random() - 0.5) * 0.18,
                r: Math.random() * 1.4 + 0.4,
                alpha: Math.random() * 0.35 + 0.08,
                phase: Math.random() * Math.PI * 2,
            }));
        };

        const step = (time: number) => {
            ctx.clearRect(0, 0, width, height);

            for (const particle of particles) {
                particle.x += particle.vx;
                particle.y += particle.vy;

                if (particle.x < -10) particle.x = width + 10;
                if (particle.x > width + 10) particle.x = -10;
                if (particle.y < -10) particle.y = height + 10;
                if (particle.y > height + 10) particle.y = -10;

                const twinkle = 0.6 + 0.4 * Math.sin(time * 0.001 + particle.phase);
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(190, 190, 200, ${particle.alpha * twinkle})`;
                ctx.fill();
            }

            animationFrame = window.requestAnimationFrame(step);
        };

        resize();
        animationFrame = window.requestAnimationFrame(step);
        window.addEventListener("resize", resize);

        return () => {
            window.removeEventListener("resize", resize);
            window.cancelAnimationFrame(animationFrame);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="fixed inset-0 pointer-events-none opacity-70"
            aria-hidden="true"
        />
    );
}
