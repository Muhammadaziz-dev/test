import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { usePathname } from "next/navigation";

const Sidebar: React.FC<Props> = ({ className, links }) => {
  const path = usePathname();

  return (
    <div
      className={cn(
        `border-r fixed bg-background left-0 w-[20%] h-screen`,
        className,
      )}
    >
      <div className={`container mt-2`}>
        <p
          className={`text-2xl uppercase font-bold cursor-pointer py-1 text-center`}
        >
          MF Platform
        </p>
      </div>
      <hr className={`mt-2`} />
      <ul className={`container mt-8 flex flex-col gap-y-1`}>
        {links.map((link, idx) => (
          <li key={idx} className={`hover:bg-accent rounded-lg`}>
            <Link href={link.path}>
              <Button
                variant={path === link.path ? "default" : "ghost"}
                className={`w-full items-center justify-start pl-8`}
                size={"sm"}
              >
                {link.label}
              </Button>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;

interface Props {
  className?: string;
  links: {
    label: string;
    path: string;
  }[];
}
