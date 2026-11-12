"use client";

import { useEffect, useRef } from "react";

/** Plain canvas physics object kept outside the React render/effect scope. */
class Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    size: number;

    constructor(width: number, height: number, speed: number) {
        this.x = Math.random() * width;
        this.y = Math.random() * height;
        this.vx = (Math.random() - 0.5) * speed;
        this.vy = (Math.random() - 0.5) * speed;
        this.size = Math.random() * 2 + 1;
    }

    update(width: number, height: number) {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > width) this.vx *= -1;
        if (this.y < 0 || this.y > height) this.vy *= -1;
    }

    draw(ctx: CanvasRenderingContext2D) {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255, 255, 255, 0.15)";
        ctx.fill();
    }
}

export function NetworkBackground() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        let width = canvas.width = window.innerWidth;
        let height = canvas.height = window.innerHeight;

        const particleCount = Math.min(Math.floor(width * height / 15000), 100);
        const particles = Array.from({ length: particleCount }, () => new Particle(width, height, 0.5));
        const connectionDistance = 150;
        let animationFrame = 0;

        const animate = () => {
            ctx.clearRect(0, 0, width, height);

            particles.forEach((particle, index) => {
                particle.update(width, height);
                particle.draw(ctx);

                for (let j = index + 1; j < particles.length; j++) {
                    const neighbour = particles[j];
                    const dx = particle.x - neighbour.x;
                    const dy = particle.y - neighbour.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < connectionDistance) {
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 * (1 - distance / connectionDistance)})`;
                        ctx.lineWidth = 1;
                        ctx.moveTo(particle.x, particle.y);
                        ctx.lineTo(neighbour.x, neighbour.y);
                        ctx.stroke();
                    }
                }
            });

            animationFrame = requestAnimationFrame(animate);
        };

        const handleResize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        };

        animationFrame = requestAnimationFrame(animate);
        window.addEventListener("resize", handleResize);

        return () => {
            cancelAnimationFrame(animationFrame);
            window.removeEventListener("resize", handleResize);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none opacity-40"
            aria-hidden="true"
        />
    );
}
