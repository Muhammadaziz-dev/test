import React, { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface Props {
  src: string;
  alt: string;
  className?: string;
  onClick?: () => void;
}

const Img: React.FC<Props> = ({ alt, src, className, onClick }) => {
  const [loading, setLoading] = useState<boolean>(true);

  const handleLoad = () => {
    setLoading(false);
  };

  return (
    <Image
      onClick={onClick}
      src={src}
      alt={alt}
      width={999}
      height={999}
      className={cn(
        "duration-300 ease-in-out",
        loading ? "blur-md" : "blur-0 bg-accent grayscale-0",
        className,
      )}
      onLoad={handleLoad}
    />
  );
};

export default Img;
