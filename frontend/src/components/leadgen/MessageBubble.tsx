import { Message } from "@/types/leadgen";
import { formatTime } from "@/lib/leadgen-utils";
import ChannelBadge from "./ChannelBadge";

export default function MessageBubble({ message }: { message: Message }) {
  const isOutbound = message.direction === "outbound";

  return (
    <div
      className={`flex gap-2 mb-3 ${isOutbound ? "flex-row-reverse" : "flex-row"}`}
    >
      {!isOutbound && (
        <div className="flex-shrink-0 mt-1">
          <ChannelBadge channel={message.channel} showLabel={false} size="md" />
        </div>
      )}

      <div
        className={`max-w-[70%] rounded-2xl px-4 py-2.5 ${
          isOutbound ? "rounded-tr-sm" : "rounded-tl-sm"
        }`}
        style={
          isOutbound
            ? { background: "#1B3A5C", color: "#fff" }
            : { background: "#F8F7F4", color: "#333333", border: "1px solid #E8E8E8" }
        }
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </p>
        <p
          className={`text-[11px] mt-1 ${isOutbound ? "text-blue-200 text-right" : "text-text-muted text-right"}`}
        >
          {formatTime(message.sent_at)}
        </p>
      </div>
    </div>
  );
}
