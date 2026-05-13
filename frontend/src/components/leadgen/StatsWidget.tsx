interface StatsWidgetProps {
  label: string;
  value: number | string;
  accentColor?: string;
}

export default function StatsWidget({
  label,
  value,
  accentColor = "#1B3A5C",
}: StatsWidgetProps) {
  return (
    <div
      className="bg-white rounded-xl p-6 shadow-card flex flex-col justify-between"
      style={{ minHeight: "120px" }}
    >
      <p className="text-sm text-text-muted">{label}</p>
      <p
        className="font-heading font-bold leading-none mt-3"
        style={{ fontSize: "48px", color: accentColor }}
      >
        {value}
      </p>
    </div>
  );
}
