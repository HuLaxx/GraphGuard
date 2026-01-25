"use client";

import { useEffect, useRef } from "react";

type DustParticle = {
    x: number;
    y: number;
    size: number;
    speedX: number;
    speedY: number;
    opacity: number;
    baseOpacity: number;
    hue: number;
    twinkleSpeed: number;
    twinklePhase: number;
    isTwinkling: boolean;
};

export function DustBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let animationFrameId = 0;
        let particles: DustParticle[] = [];

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };

        const createParticles = () => {
            particles = [];
            const particleCount = Math.floor((canvas.width * canvas.height) / 15000);

            for (let i = 0; i < particleCount; i++) {
                const baseOpacity = Math.random() * 0.5 + 0.2;
                particles.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    size: Math.random() * Math.random() * 2.7 + 0.3,
                    speedX: (Math.random() - 0.5) * 0.3,
                    speedY: (Math.random() - 0.5) * 0.3,
                    opacity: baseOpacity,
                    baseOpacity: baseOpacity,
                    hue: 210 + Math.random() * 25,
                    twinkleSpeed: Math.random() * 0.008 + 0.002,
                    twinklePhase: Math.random() * Math.PI * 2,
                    isTwinkling: Math.random() > 0.6,
                });
            }
        };

        const drawParticle = (particle: DustParticle) => {
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${particle.hue}, 14%, 76%, ${particle.opacity})`;
            ctx.fill();

            ctx.shadowBlur = particle.size * 4;
            ctx.shadowColor = `hsla(${particle.hue}, 20%, 68%, ${particle.opacity * 0.45})`;
            ctx.fill();
            ctx.shadowBlur = 0;
        };

        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach((particle) => {
                particle.x += particle.speedX;
                particle.y += particle.speedY;

                if (particle.x < 0) particle.x = canvas.width;
                if (particle.x > canvas.width) particle.x = 0;
                if (particle.y < 0) particle.y = canvas.height;
                if (particle.y > canvas.height) particle.y = 0;

                if (particle.isTwinkling) {
                    particle.twinklePhase += particle.twinkleSpeed;
                    const twinkleFactor = Math.sin(particle.twinklePhase);
                    particle.opacity = particle.baseOpacity * (0.3 + twinkleFactor * 0.7);
                }

                drawParticle(particle);
            });

            animationFrameId = window.requestAnimationFrame(animate);
        };

        const handleResize = () => {
            resize();
            createParticles();
        };

        resize();
        createParticles();
        animate();

        window.addEventListener("resize", handleResize);

        return () => {
            window.cancelAnimationFrame(animationFrameId);
            window.removeEventListener("resize", handleResize);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="fixed inset-0 pointer-events-none z-0 opacity-60"
            style={{ mixBlendMode: "screen" }}
            aria-hidden="true"
        />
    );
}
