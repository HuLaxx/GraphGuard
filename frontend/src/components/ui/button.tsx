import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
    "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:pointer-events-none disabled:opacity-50",
    {
        variants: {
            variant: {
                default: "bg-gradient-to-r from-zinc-100 to-zinc-400 text-zinc-950 shadow-lg shadow-zinc-500/20 hover:shadow-zinc-500/40 hover:scale-[1.02] hover:from-white hover:to-zinc-300",
                destructive: "bg-red-600 text-white hover:bg-red-700",
                outline: "border border-zinc-700 bg-zinc-900/80 text-zinc-100 hover:bg-zinc-800 hover:border-zinc-600 backdrop-blur-sm",
                secondary: "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
                ghost: "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50",
                link: "text-zinc-100 underline-offset-4 hover:underline",
                success: "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20",
                warning: "bg-amber-500/10 border border-amber-500/20 text-amber-400 hover:bg-amber-500/20",
            },
            size: {
                default: "h-10 px-6",
                sm: "h-9 px-4 text-xs",
                lg: "h-12 px-8 text-base",
                icon: "h-10 w-10",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
);

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
    asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant, size, asChild = false, ...props }, ref) => {
        const Comp = asChild ? Slot : "button";
        return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
    }
);
Button.displayName = "Button";

export { Button, buttonVariants };
