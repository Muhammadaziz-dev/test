import React, { ReactElement } from "react";
import { Sheet, SheetContent, SheetFooter } from "@/components/ui/sheet";
import { X } from "lucide-react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Props {
  open: boolean;
  setOpen: (open: boolean) => void;
  side?: "left" | "right" | "bottom" | "top";
  body: ReactElement;
  className?: string;
  title?: string;
  footer?: React.ReactElement;
}

const drawerX = cva(
  "cursor-pointer  hover:rotate-180 absolute text-xl transition duration-700",
  {
    variants: {
      side: {
        top: "bottom-4 left-4",
        bottom: "top-4 left-4",
        left: "right-4 top-4",
        right: "left-4 top-4",
      },
    },
    defaultVariants: {
      side: "right",
    },
  },
);

const Drawer: React.FC<Props> = ({
  open,
  setOpen,
  side = "right",
  body,
  className,
  title,
  footer,
}) => {
  return (
    <>
      <Sheet open={open} onOpenChange={() => setOpen(open)}>
        <SheetContent className={className} side={side}>
          <p
            className={`absolute top-4 uppercase font-medium text-xl ${side}-4`}
          >
            {title}
          </p>
          <X
            size={30}
            onClick={() => setOpen(open)}
            className={cn(drawerX({ side }))}
          />
          <ScrollArea className={`${footer ? "h-[85%]" : "max-h-full"} mt-8`}>
            {body}
          </ScrollArea>
          <SheetFooter className={`${footer && "h-fit"} border-t pt-2`}>
            {footer}
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
};

export default Drawer;
