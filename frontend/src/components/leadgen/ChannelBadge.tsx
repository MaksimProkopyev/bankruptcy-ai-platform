import { Mail, Globe, Phone, PhoneCall, Send } from "lucide-react";
import { Channel } from "@/types/leadgen";

interface ChannelConfig {
  icon: React.ReactNode;
  label: string;
  bg: string;
}

const CHANNEL_CONFIG: Record<Channel, ChannelConfig> = {
  telegram: {
    icon: <Send className="w-3 h-3" />,
    label: "Telegram",
    bg: "#2AABEE",
  },
  whatsapp: {
    icon: <Phone className="w-3 h-3" />,
    label: "WhatsApp",
    bg: "#25D366",
  },
  vk: {
    icon: <span className="text-[10px] font-bold leading-none">VK</span>,
    label: "ВКонтакте",
    bg: "#0077FF",
  },
  email: {
    icon: <Mail className="w-3 h-3" />,
    label: "Email",
    bg: "#EA4335",
  },
  ok: {
    icon: <span className="text-[10px] font-bold leading-none">OK</span>,
    label: "Одноклассники",
    bg: "#FF7700",
  },
  facebook: {
    icon: <span className="text-[10px] font-bold leading-none">f</span>,
    label: "Facebook",
    bg: "#1877F2",
  },
  avito: {
    icon: <span className="text-[10px] font-bold leading-none">A</span>,
    label: "Авито",
    bg: "#00A046",
  },
  callback: {
    icon: <PhoneCall className="w-3 h-3" />,
    label: "Callback",
    bg: "#6B7280",
  },
  web: {
    icon: <Globe className="w-3 h-3" />,
    label: "Web",
    bg: "#3B82F6",
  },
  max: {
    icon: <span className="text-[10px] font-bold leading-none">M</span>,
    label: "Max",
    bg: "#7C3AED",
  },
};

interface ChannelBadgeProps {
  channel: Channel;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export default function ChannelBadge({
  channel,
  showLabel = true,
  size = "sm",
}: ChannelBadgeProps) {
  const config = CHANNEL_CONFIG[channel] ?? {
    icon: <Globe className="w-3 h-3" />,
    label: channel,
    bg: "#6B7280",
  };

  const iconSize = size === "md" ? "w-5 h-5" : "w-4 h-4";

  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex items-center justify-center rounded-full text-white flex-shrink-0 ${iconSize}`}
        style={{ background: config.bg }}
      >
        {config.icon}
      </span>
      {showLabel && (
        <span className="text-xs text-text-muted">{config.label}</span>
      )}
    </span>
  );
}
