"use client";
import React, { useEffect, useRef } from "react";

interface AnimatedValueProps {
  start?: number;
  end: number;
  duration?: number;
  className?: string;
}

const formatNumber = (number: number): string => {
  if (number >= 1000000) {
    return (number / 1000000).toFixed(1) + "M";
  }
  if (number >= 1000) {
    return (number / 1000).toFixed(1) + "K";
  }
  return number.toString();
};

const AnimatedValue: React.FC<AnimatedValueProps> = ({
  start = 0,
  end,
  duration = 300,
  className,
}) => {
  const objRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const obj = objRef.current;
    let startTimestamp: number | null = null;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const currentValue = Math.floor(progress * (end - start) + start);
      if (obj) {
        obj.innerHTML = formatNumber(currentValue);
      }
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };

    if (obj) {
      window.requestAnimationFrame(step);
    }

    return () => {
      if (obj) {
        obj.innerHTML = formatNumber(end);
      }
    };
  }, [start, end, duration]);

  return <span className={className} ref={objRef} />;
};

export default AnimatedValue;
