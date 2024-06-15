import React from "react";
import { Dialog, DialogContent, DialogFooter } from "@/components/ui/dialog";
import { X } from "lucide-react";

interface Props {
  body: React.ReactElement;
  open: boolean;
  setOpen: (e: boolean) => void;
  title?: string;
  footer?: React.ReactElement;
  className?: string;
}

const Modal: React.FC<Props> = ({
  body,
  className,
  footer,
  open,
  setOpen,
  title,
}) => {
  return (
    <Dialog open={open} onOpenChange={() => setOpen(!open)}>
      <DialogContent className={className}>
        <div className="flex items-center gap-6 relative justify-center">
          <button
            onClick={() => setOpen(!open)}
            className="p-0 w-fit absolute top-0 right-0"
          >
            <X size={26} />
          </button>
          <p className={`text-center text-xl font-medium w-full`}>{title}</p>
        </div>
        <div>{body}</div>
        <DialogFooter>{footer}</DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default Modal;
