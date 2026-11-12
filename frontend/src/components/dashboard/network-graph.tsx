"use client";

import { memo, useEffect, useRef } from "react";
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

type SimulationNode = GraphNode & d3.SimulationNodeDatum;
type SimulationLink = d3.SimulationLinkDatum<SimulationNode> & Omit<GraphLink, "source" | "target">;

const COLORS = {
    fraud: "#ef4444",
    user: "#fafafa",
    merchant: "#a1a1aa",
    device: "#52525b",
    link: "#27272a",
    highlight: "#10b981",
};

const nodeX = (node: SimulationLink["source"]) =>
    typeof node === "object" ? node.x ?? 0 : 0;
const nodeY = (node: SimulationLink["source"]) =>
    typeof node === "object" ? node.y ?? 0 : 0;

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

        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();
        svg.attr("width", width).attr("height", height).attr("viewBox", `0 0 ${width} ${height}`);

        // D3 mutates coordinates and link endpoints, so never mutate React props.
        const simulationNodes: SimulationNode[] = nodes.map(node => ({ ...node }));
        const simulationLinks: SimulationLink[] = links.map(link => ({ ...link }));

        const container = svg.append("g");
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 4])
            .on("zoom", event => container.attr("transform", event.transform.toString()));
        svg.call(zoom);

        const simulation = d3.forceSimulation<SimulationNode>(simulationNodes)
            .force("link", d3.forceLink<SimulationNode, SimulationLink>(simulationLinks)
                .id(node => node.id)
                .distance(80))
            .force("charge", d3.forceManyBody<SimulationNode>().strength(-250))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide<SimulationNode>().radius(25));

        const link = container.append("g").attr("class", "links")
            .selectAll<SVGLineElement, SimulationLink>("line")
            .data(simulationLinks).join("line")
            .attr("stroke", COLORS.link)
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", item => Math.max(1, Math.sqrt((item.amount ?? 100) / 500)));

        const node = container.append("g").attr("class", "nodes")
            .selectAll<SVGCircleElement, SimulationNode>("circle")
            .data(simulationNodes).join("circle")
            .attr("r", item => 8 + (item.pagerank || 0) * 200)
            .attr("fill", item => {
                if (item.fraud) return COLORS.fraud;
                switch (item.type) {
                    case "MERCHANT": return COLORS.merchant;
                    case "DEVICE": return COLORS.device;
                    case "USER": return COLORS.user;
                    default: return COLORS.user;
                }
            })
            .attr("stroke", "#18181b")
            .attr("stroke-width", 2)
            .style("cursor", "pointer")
            .on("click", (_event, item) => onNodeClick?.(item))
            .on("mouseover", function () {
                d3.select(this).attr("stroke", COLORS.highlight).attr("stroke-width", 3);
            })
            .on("mouseout", function () {
                d3.select(this).attr("stroke", "#18181b").attr("stroke-width", 2);
            });

        const drag = d3.drag<SVGCircleElement, SimulationNode>()
            .on("start", event => {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            })
            .on("drag", event => {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            })
            .on("end", event => {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            });
        node.call(drag);

        const label = container.append("g").attr("class", "labels")
            .selectAll<SVGTextElement, SimulationNode>("text")
            .data(simulationNodes).join("text")
            .text(item => item.label || item.id.slice(0, 8))
            .attr("font-size", 10)
            .attr("font-family", "var(--font-sans)")
            .attr("fill", "#71717a")
            .attr("dx", 12)
            .attr("dy", 4);

        node.append("title").text(item =>
            `${item.id}\nType: ${item.type}\nRisk: ${(item.riskScore || 0).toFixed(2)}\nFraud: ${item.fraud ? "Yes" : "No"}`
        );

        simulation.on("tick", () => {
            link.attr("x1", item => nodeX(item.source))
                .attr("y1", item => nodeY(item.source))
                .attr("x2", item => nodeX(item.target))
                .attr("y2", item => nodeY(item.target));
            node.attr("cx", item => item.x ?? 0).attr("cy", item => item.y ?? 0);
            label.attr("x", item => item.x ?? 0).attr("y", item => item.y ?? 0);
        });

        return () => { simulation.stop(); };
    }, [nodes, links, width, height, onNodeClick]);

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-lg">Transaction Network</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
                <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3">
                    <svg ref={svgRef} className="w-full" aria-label="Transaction relationship graph" role="img" />
                </div>
                <div className="flex flex-wrap gap-4 mt-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500" /> Fraudster</span>
                    <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-zinc-50" /> User</span>
                    <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-zinc-400" /> Merchant</span>
                    <span className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-zinc-600" /> Device</span>
                </div>
            </CardContent>
        </Card>
    );
}

export const NetworkGraph = memo(NetworkGraphComponent);
