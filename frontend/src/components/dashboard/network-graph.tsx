"use client";

import { useRef, useEffect, memo } from "react";
import * as d3 from "d3";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GraphNode, GraphLink } from "@/types";

interface NetworkGraphProps {
    nodes: GraphNode[];
    links: GraphLink[];
    width?: number;
    height?: number;
    onNodeClick?: (node: GraphNode) => void;
}

const COLORS = {
    fraud: "#ef4444",      // Semantic Red for Danger
    user: "#fafafa",       // Zinc-50 (High Contrast)
    merchant: "#a1a1aa",   // Zinc-400 (Subtle)
    device: "#52525b",     // Zinc-600 (Darker)
    link: "#27272a",       // Zinc-800
    highlight: "#10b981",  // Emerald-500 for hover (matches "Live System")
};

function NetworkGraphComponent({
    nodes,
    links,
    width = 500,
    height = 400,
    onNodeClick,
}: NetworkGraphProps) {
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!svgRef.current || nodes.length === 0) return;

        d3.select(svgRef.current).selectAll("*").remove();

        const svg = d3
            .select(svgRef.current)
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height] as any);

        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 4])
            .on("zoom", (event) => container.attr("transform", event.transform));

        svg.call(zoom);
        const container = svg.append("g");

        const simulation = d3
            .forceSimulation(nodes as any)
            .force("link", d3.forceLink(links).id((d: any) => d.id).distance(80))
            .force("charge", d3.forceManyBody().strength(-250))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(25));

        const link = container
            .append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke", COLORS.link)
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", (d: any) => Math.max(1, Math.sqrt((d.amount || 100) / 500)));

        const node = container
            .append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(nodes)
            .join("circle")
            .attr("r", (d: any) => 8 + (d.pagerank || 0) * 200)
            .attr("fill", (d: any) => {
                if (d.fraud) return COLORS.fraud;
                switch (d.type) {
                    case "USER": return COLORS.user;
                    case "MERCHANT": return COLORS.merchant;
                    case "DEVICE": return COLORS.device;
                    default: return COLORS.user;
                }
            })
            .attr("stroke", "#18181b")
            .attr("stroke-width", 2)
            .style("cursor", "pointer")
            .on("click", (event, d: any) => onNodeClick?.(d))
            .on("mouseover", function () {
                d3.select(this).attr("stroke", COLORS.highlight).attr("stroke-width", 3);
            })
            .on("mouseout", function () {
                d3.select(this).attr("stroke", "#18181b").attr("stroke-width", 2);
            })
            .call(drag(simulation) as any);

        const label = container
            .append("g")
            .attr("class", "labels")
            .selectAll("text")
            .data(nodes)
            .join("text")
            .text((d: any) => d.label || d.id.slice(0, 8))
            .attr("font-size", 10)
            .attr("font-family", "var(--font-sans)")
            .attr("fill", "#71717a")
            .attr("dx", 12)
            .attr("dy", 4);

        node.append("title").text(
            (d: any) =>
                `${d.id}\nType: ${d.type}\nRisk: ${(d.riskScore || 0).toFixed(2)}\nFraud: ${d.fraud ? "Yes" : "No"}`
        );

        simulation.on("tick", () => {
            link
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);
            node.attr("cx", (d: any) => d.x).attr("cy", (d: any) => d.y);
            label.attr("x", (d: any) => d.x).attr("y", (d: any) => d.y);
        });

        function drag(simulation: any) {
            return d3.drag()
                .on("start", (event: any) => {
                    if (!event.active) simulation.alphaTarget(0.3).restart();
                    event.subject.fx = event.subject.x;
                    event.subject.fy = event.subject.y;
                })
                .on("drag", (event: any) => {
                    event.subject.fx = event.x;
                    event.subject.fy = event.y;
                })
                .on("end", (event: any) => {
                    if (!event.active) simulation.alphaTarget(0);
                    event.subject.fx = null;
                    event.subject.fy = null;
                });
        }

        return () => {
            simulation.stop();
        };
    }, [nodes, links, width, height, onNodeClick]);

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-lg">Transaction Network</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
                    <svg ref={svgRef} className="w-full" />
                </div>
                <div className="flex flex-wrap gap-4 mt-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-red-500" /> Fraudster
                    </span>
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-zinc-50" /> User
                    </span>
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-zinc-400" /> Merchant
                    </span>
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-zinc-600" /> Device
                    </span>
                </div>
            </CardContent>
        </Card>
    );
}

export const NetworkGraph = memo(NetworkGraphComponent);
