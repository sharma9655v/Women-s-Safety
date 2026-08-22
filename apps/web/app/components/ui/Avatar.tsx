const COLORS = [
  "bg-primary text-white",
  "bg-accent text-white",
  "bg-secondary text-white",
  "bg-info text-white",
  "bg-warning text-black",
  "bg-success text-white",
];

export function Avatar({
  initials,
  label,
  index = 0,
  size = "md",
}: {
  initials: string;
  label: string;
  index?: number;
  size?: "sm" | "md" | "lg";
}) {
  const color = COLORS[index % COLORS.length];
  const sizes = {
    sm: "size-7 text-[10px]",
    md: "size-8 text-xs",
    lg: "size-10 text-sm",
  };

  return (
    <span
      role="img"
      aria-label={label}
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${color} ${sizes[size]}`}
    >
      {initials}
    </span>
  );
}
