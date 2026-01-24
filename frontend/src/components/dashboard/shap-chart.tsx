"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ShapFeature } from "@/types";

interface ShapChartProps {
    features: ShapFeature[];
    predictionValue: number;
    plainEnglish?: string;
}

export function ShapChart({ features, predictionValue, plainEnglish }: ShapChartProps) {
    const sortedFeatures = [...features].sort((a, b) => Math.abs(b.shapValue) - Math.abs(a.shapValue)).slice(0, 8);
    const maxAbsValue = Math.max(...sortedFeatures.map((f) => Math.abs(f.shapValue)), 0.01);

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center justify-between">
                    <span>Model Explanation</span>
                    <span
                        className={cn(
                            "text-xs font-semibold px-3 py-1 rounded-full",
                            predictionValue > 0.7 ? "bg-red-500/10 text-red-400 border border-red-500/20" :
                                predictionValue > 0.4 ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                    "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        )}
                    >
                        {(predictionValue * 100).toFixed(0)}% risk
                    </span>
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                {plainEnglish && (
                    <div className="px-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-xl text-sm text-zinc-300">
                        {plainEnglish}
                    </div>
                )}

                <div className="space-y-2">
                    {sortedFeatures.map((feature) => {
                        const isPositive = feature.shapValue > 0;
                        const width = (Math.abs(feature.shapValue) / maxAbsValue) * 50;

                        return (
                            <div key={feature.name} className="flex items-center gap-3 text-sm">
                                <span className="w-36 truncate text-zinc-400 text-right">{feature.name}</span>
                                <div className="flex-1 h-5 relative">
                                    <div className="absolute left-1/2 h-full w-px bg-zinc-700" />
                                    <div
                                        className={cn(
                                            "absolute h-full rounded-full",
                                            isPositive ? "bg-red-500" : "bg-emerald-500"
                                        )}
                                        style={{
                                            width: `${width}%`,
                                            left: isPositive ? "50%" : `${50 - width}%`,
                                        }}
                                    />
                                </div>
                                <span className="w-16 text-xs text-zinc-500 tabular-nums">
                                    {feature.shapValue > 0 ? "+" : ""}{feature.shapValue.toFixed(3)}
                                </span>
                            </div>
                        );
                    })}
                </div>

                <div className="flex justify-center gap-6 text-xs text-zinc-500 pt-2">
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 bg-red-500 rounded-full" /> Increases risk
                    </span>
                    <span className="flex items-center gap-2">
                        <span className="w-3 h-3 bg-emerald-500 rounded-full" /> Decreases risk
                    </span>
                </div>
            </CardContent>
        </Card>
    );
}
