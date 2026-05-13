"use client";

import { useState, useRef, KeyboardEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";

interface MessageInputProps {
  onSend: (content: string) => Promise<void>;
  disabled?: boolean;
}

export default function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSend() {
    const content = text.trim();
    if (!content || sending) return;

    setSending(true);
    try {
      await onSend(content);
      setText("");
      textareaRef.current?.focus();
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div
      className="flex gap-2 p-3 border-t border-neutral bg-white"
    >
      <Textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите сообщение… (Ctrl+Enter для отправки)"
        rows={2}
        disabled={disabled || sending}
        className="resize-none flex-1 text-sm"
        style={{ minHeight: "64px", maxHeight: "160px" }}
      />
      <Button
        onClick={handleSend}
        disabled={!text.trim() || sending || disabled}
        className="self-end flex-shrink-0"
        style={
          text.trim() && !sending
            ? { background: "#C9A84C", color: "#fff", borderColor: "#C9A84C" }
            : {}
        }
      >
        {sending ? (
          <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
}
