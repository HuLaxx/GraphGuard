/**
 * GraphGuard - D3 Network Graph Component
 * =========================================
 * File: frontend/src/components/NetworkGraph.tsx
 * Reference: Specification.md Lines 3286-3431
 *
 * Goal: Interactive D3 force-directed graph for visualizing transaction networks.
 *
 * Gotchas (from spec):
 * - D3 force simulation is CPU-intensive - limit to <200 nodes
 * - Use React.memo() to prevent re-rendering on parent state changes
 */

import React, { useRef, useEffect, memo } from 'react';
import * as d3 from 'd3';

// ============================================
// Types
// ============================================

export interface GraphNode {
    id: string;
    type: 'USER' | 'MERCHANT' | 'DEVICE';
    label: string;
    fraud: boolean;
    pagerank: number;
    riskScore: number;
}

export interface GraphLink {
    source: string;
    target: string;
    amount: number;
    type: string;
}

export interface NetworkGraphProps {
    nodes: GraphNode[];
    links: GraphLink[];
    width?: number;
    height?: number;
    onNodeClick?: (node: GraphNode) => void;
}

// ============================================
// Color Scheme
// ============================================

const COLORS = {
    fraud: '#f44336',      // Red
    user: '#2196f3',       // Blue
    merchant: '#4caf50',   // Green
    device: '#ff9800',     // Orange
    link: '#999',
    highlight: '#ffeb3b'
};

// ============================================
// Component
// ============================================

const NetworkGraphComponent: React.FC<NetworkGraphProps> = ({
    nodes,
    links,
    width = 800,
    height = 600,
    onNodeClick
}) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!svgRef.current || nodes.length === 0) return;

        // Clear previous
        d3.select(svgRef.current).selectAll('*').remove();

        const svg = d3.select(svgRef.current)
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', [0, 0, width, height] as any);

        // Add zoom behavior
        const zoom = d3.zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.5, 5])
            .on('zoom', (event) => {
                container.attr('transform', event.transform);
            });

        svg.call(zoom);

        const container = svg.append('g');

        // Create arrow marker for directed edges
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', COLORS.link);

        // Force simulation
        const simulation = d3.forceSimulation(nodes as any)
            .force('link', d3.forceLink(links).id((d: any) => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        // Links
        const link = container.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', COLORS.link)
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', (d: any) => Math.max(1, Math.sqrt(d.amount / 100)))
            .attr('marker-end', 'url(#arrowhead)');

        // Nodes
        const node = container.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(nodes)
            .join('circle')
            .attr('r', (d: any) => 8 + (d.pagerank || 0) * 50)
            .attr('fill', (d: any) => {
                if (d.fraud) return COLORS.fraud;
                switch (d.type) {
                    case 'USER': return COLORS.user;
                    case 'MERCHANT': return COLORS.merchant;
                    case 'DEVICE': return COLORS.device;
                    default: return COLORS.user;
                }
            })
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .on('click', (event, d: any) => {
                if (onNodeClick) onNodeClick(d);
            })
            .on('mouseover', function () {
                d3.select(this)
                    .attr('stroke', COLORS.highlight)
                    .attr('stroke-width', 4);
            })
            .on('mouseout', function () {
                d3.select(this)
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2);
            })
            .call(drag(simulation) as any);

        // Labels
        const label = container.append('g')
            .attr('class', 'labels')
            .selectAll('text')
            .data(nodes)
            .join('text')
            .text((d: any) => d.label || d.id.slice(0, 8))
            .attr('font-size', 10)
            .attr('font-family', 'Arial, sans-serif')
            .attr('dx', 12)
            .attr('dy', 4)
            .attr('fill', '#333');

        // Tooltip
        node.append('title')
            .text((d: any) =>
                `${d.id}\nType: ${d.type}\nPageRank: ${(d.pagerank || 0).toFixed(3)}\nRisk: ${(d.riskScore || 0).toFixed(2)}\nFraud: ${d.fraud ? 'Yes' : 'No'}`
            );

        // Update positions on tick
        simulation.on('tick', () => {
            link
                .attr('x1', (d: any) => d.source.x)
                .attr('y1', (d: any) => d.source.y)
                .attr('x2', (d: any) => d.target.x)
                .attr('y2', (d: any) => d.target.y);

            node
                .attr('cx', (d: any) => d.x)
                .attr('cy', (d: any) => d.y);

            label
                .attr('x', (d: any) => d.x)
                .attr('y', (d: any) => d.y);
        });

        // Drag behavior
        function drag(simulation: any) {
            function dragstarted(event: any) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }

            function dragged(event: any) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }

            function dragended(event: any) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }

            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        }

        // Cleanup
        return () => {
            simulation.stop();
        };
    }, [nodes, links, width, height, onNodeClick]);

    return (
        <div ref={containerRef} className="network-graph-container">
            <svg ref={svgRef}></svg>
            <div className="legend" style={{ marginTop: '10px', display: 'flex', gap: '20px' }}>
                <span style={{ color: COLORS.fraud }}>o Fraudster</span>
                <span style={{ color: COLORS.user }}>o User</span>
                <span style={{ color: COLORS.merchant }}>o Merchant</span>
                <span style={{ color: COLORS.device }}>o Device</span>
            </div>
            <style>{`
        .network-graph-container {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 16px;
          background: #fafafa;
        }
        .legend {
          font-size: 14px;
          font-family: Arial, sans-serif;
        }
      `}</style>
        </div>
    );
};

// Memoize to prevent unnecessary re-renders
export const NetworkGraph = memo(NetworkGraphComponent);
