import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
    {
        variants: {
            variant: {
                default: "border-transparent bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
                secondary: "border-zinc-700 bg-zinc-900/80 text-zinc-400 hover:text-zinc-100",
                destructive: "border-transparent bg-red-500/10 text-red-400",
                outline: "border-zinc-700 text-zinc-400",
                success: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
                warning: "border-amber-500/20 bg-amber-500/10 text-amber-400",
                info: "border-cyan-500/20 bg-cyan-500/10 text-cyan-400",
                critical: "border-transparent bg-red-600 text-white",
                high: "border-transparent bg-red-500 text-white",
                medium: "border-transparent bg-amber-500 text-zinc-900",
                low: "border-transparent bg-emerald-500 text-zinc-900",
            },
        },
        defaultVariants: {
            variant: "default",
        },
    }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
