"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface TiltProps {
  children: ReactNode;
  className?: string;
}

export function Tilt({ children, className = "" }: TiltProps) {
  return (
    <motion.div
      whileHover={{ scale: 1.02, rotateX: -2, rotateY: 2 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      style={{ perspective: 800, transformStyle: "preserve-3d" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
