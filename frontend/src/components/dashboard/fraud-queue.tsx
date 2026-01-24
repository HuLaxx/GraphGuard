"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency, formatDate, formatPercent, getPriorityColor, getStatusColor } from "@/lib/utils";
import type { FraudCase } from "@/types";

interface FraudQueueProps {
    cases: FraudCase[];
    selectedId?: string;
    onSelect: (fraudCase: FraudCase) => void;
}

export function FraudQueue({ cases, selectedId, onSelect }: FraudQueueProps) {
    if (cases.length === 0) {
        return (
            <Card>
                <CardContent className="p-8 text-center text-zinc-500">No pending cases</CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center justify-between">
                    <span>Live Case Queue</span>
                    <Badge variant="secondary" className="text-xs">
                        {cases.length} active
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-zinc-800 text-xs uppercase tracking-widest text-zinc-500">
                                <th className="py-3 px-4 text-left font-medium">Priority</th>
                                <th className="py-3 px-4 text-left font-medium">Score</th>
                                <th className="py-3 px-4 text-left font-medium">Amount</th>
                                <th className="py-3 px-4 text-left font-medium">User</th>
                                <th className="py-3 px-4 text-left font-medium">Status</th>
                                <th className="py-3 px-4 text-left font-medium">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cases.map((fraudCase) => (
                                <tr
                                    key={fraudCase.id}
                                    onClick={() => onSelect(fraudCase)}
                                    className={cn(
                                        "border-b border-zinc-800/50 cursor-pointer transition-colors hover:bg-zinc-800/50",
                                        selectedId === fraudCase.id && "bg-zinc-800/80"
                                    )}
                                >
                                    <td className="py-3 px-4">
                                        <Badge className={cn("text-xs", getPriorityColor(fraudCase.priority))}>
                                            {fraudCase.priority}
                                        </Badge>
                                    </td>
                                    <td className="py-3 px-4 font-mono text-zinc-100">
                                        {formatPercent(fraudCase.fraudScore, 0)}
                                    </td>
                                    <td className="py-3 px-4 text-zinc-100">{formatCurrency(fraudCase.amount)}</td>
                                    <td className="py-3 px-4 text-zinc-400">{fraudCase.userId}</td>
                                    <td className="py-3 px-4">
                                        <Badge className={cn("text-xs", getStatusColor(fraudCase.status))}>
                                            {fraudCase.status.replace("_", " ")}
                                        </Badge>
                                    </td>
                                    <td className="py-3 px-4 text-zinc-500 text-xs">{formatDate(fraudCase.createdAt)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}
