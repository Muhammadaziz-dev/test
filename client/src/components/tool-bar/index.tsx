import React from "react";
import { cn } from "@/lib/utils";
import { ThemeModeToggle } from "@/components/togglies/theme.toggle";

const Toolbar: React.FC<Props> = ({ className }) => {
  return (
    <div
      className={cn(
        "border-l bg-background fixed flex flex-col items-center py-2 right-0 w-[5%] h-screen",
        className,
      )}
    >
      <div>
        <ThemeModeToggle />
      </div>
    </div>
  );
};

export default Toolbar;

interface Props {
  className?: string;
}
