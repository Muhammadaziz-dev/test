"use client";
import React, { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface Props {
  options: {
    label: any;
    value: any;
  }[];

  className?: string;
  placeholder?: string;
  onChange: (value: any) => void;
  value: any;
  id: string;
}

const Combobox: React.FC<Props> = ({
  options,
  onChange,
  className,
  placeholder,
  value,
  id,
}) => {
  const [filter, setFilter] = useState<string>("");

  return (
    <Select defaultValue={value} onValueChange={(value) => onChange(value)}>
      <SelectTrigger id={id} className={cn("", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <div className={`m-2 mb-3`}>
          <Input
            placeholder={`Search ...`}
            autoFocus={true}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        {options
          .filter((product) =>
            product.label.toLowerCase().includes(filter.toLowerCase()),
          )
          .map((option, index) => (
            <SelectItem key={index} className="uppercase" value={option.value}>
              {option.label}
            </SelectItem>
          ))}
      </SelectContent>
    </Select>
  );
};

export default Combobox;
