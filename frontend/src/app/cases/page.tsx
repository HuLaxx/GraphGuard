"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { FraudQueue, NetworkGraph } from "@/components/dashboard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency, formatDate, formatPercent, getPriorityColor } from "@/lib/utils";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import type { FraudCase, GraphNode, GraphLink } from "@/types";

const mockCases: FraudCase[] = [
    { id: "case_101", transactionId: "txn_81e1c", fraudScore: 0.89, status: "PENDING", priority: "HIGH", amount: 2120, currency: "USD", userId: "user_4392", merchantName: "Marketplace Prime", createdAt: new Date().toISOString() },
    { id: "case_102", transactionId: "txn_74aa1", fraudScore: 0.74, status: "IN_REVIEW", priority: "MEDIUM", amount: 820, currency: "USD", userId: "user_2218", merchantName: "Digital Goods", createdAt: new Date(Date.now() - 5400000).toISOString() },
    { id: "case_103", transactionId: "txn_92bb2", fraudScore: 0.67, status: "PENDING", priority: "LOW", amount: 190, currency: "EUR", userId: "user_5321", merchantName: "Streaming Media", createdAt: new Date(Date.now() - 9000000).toISOString() },
];

const mockGraphNodes: GraphNode[] = [
    { id: "user_4392", type: "USER", label: "Target User", fraud: true, pagerank: 0.022, riskScore: 0.89 },
    { id: "user_7421", type: "USER", label: "Connected User", fraud: true, pagerank: 0.016, riskScore: 0.74 },
    { id: "merchant_482", type: "MERCHANT", label: "Marketplace Prime", fraud: false, pagerank: 0.039, riskScore: 0.65 },
    { id: "device_400", type: "DEVICE", label: "Shared Device", fraud: false, pagerank: 0.006, riskScore: 0.58 },
];

const mockGraphLinks: GraphLink[] = [
    { source: "user_4392", target: "merchant_482", type: "TRANSACTED_WITH", amount: 2120 },
    { source: "user_7421", target: "merchant_482", type: "TRANSACTED_WITH", amount: 1640 },
    { source: "user_4392", target: "device_400", type: "USES_DEVICE" },
];

const mockTimeline = [
    { label: "Device fingerprint linked to two accounts", time: "09:12" },
    { label: "Velocity spike detected across 3 merchants", time: "09:18" },
    { label: "Risk score escalated above 0.8", time: "09:21" },
    { label: "Case opened for analyst review", time: "09:25" },
];

export default function CasesPage() {
    const [selectedCase, setSelectedCase] = useState<FraudCase | null>(mockCases[0]);
    const focusCase = selectedCase || mockCases[0];

    return (
        <div className="min-h-screen bg-background">
            <Header />

            <main className="container pb-16 pt-10 space-y-8">
                <section className="space-y-3 animate-rise">
                    <span className="capsule">Investigation desk</span>
                    <h1 className="font-display text-4xl text-slate-900">Active investigations</h1>
                    <p className="text-slate-600 max-w-2xl">
                        Prioritize high-risk cases, validate network context, and resolve alerts with audit-ready notes.
                    </p>
                </section>

                <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
                    <FraudQueue
                        cases={mockCases}
                        selectedId={selectedCase?.id}
                        onSelect={setSelectedCase}
                    />

                    <div className="space-y-4">
                        <Card className="surface">
                            <CardHeader className="pb-2">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <CardTitle className="text-lg font-display">Case {focusCase.id}</CardTitle>
                                        <p className="text-sm text-slate-500 mt-1">
                                            {formatCurrency(focusCase.amount, focusCase.currency)} * {focusCase.merchantName}
                                        </p>
                                    </div>
                                    <Badge className={cn("rounded-full", getPriorityColor(focusCase.priority))}>
                                        {focusCase.priority}
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-2 gap-3 text-sm text-slate-600">
                                    <div>
                                        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Risk score</p>
                                        <p className="font-semibold text-slate-900">{formatPercent(focusCase.fraudScore, 0)}</p>
                                    </div>
                                    <div>
                                        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Status</p>
                                        <p className="font-semibold text-slate-900">{focusCase.status.replace("_", " ")}</p>
                                    </div>
                                    <div>
                                        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Transaction</p>
                                        <p className="font-semibold text-slate-900">{focusCase.transactionId}</p>
                                    </div>
                                    <div>
                                        <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Detected</p>
                                        <p className="font-semibold text-slate-900">{formatDate(focusCase.createdAt)}</p>
                                    </div>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <Button variant="success" size="sm">
                                        <CheckCircle className="h-4 w-4 mr-1" /> Legitimate
                                    </Button>
                                    <Button variant="destructive" size="sm">
                                        <XCircle className="h-4 w-4 mr-1" /> Fraud
                                    </Button>
                                    <Button variant="warning" size="sm">
                                        <AlertTriangle className="h-4 w-4 mr-1" /> Escalate
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="surface">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base font-display">Investigation timeline</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {mockTimeline.map((item, index) => (
                                    <div key={index} className="flex items-start gap-3">
                                        <div className="h-2 w-2 mt-2 rounded-full bg-rose-500" />
                                        <div>
                                            <p className="text-sm text-slate-700">{item.label}</p>
                                            <p className="text-xs text-slate-400">{item.time}</p>
                                        </div>
                                    </div>
                                ))}
                            </CardContent>
                        </Card>

                        <NetworkGraph nodes={mockGraphNodes} links={mockGraphLinks} height={260} />
                    </div>
                </div>
            </main>

            <Footer />
        </div>
    );
}
