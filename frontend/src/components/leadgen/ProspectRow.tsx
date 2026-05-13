"use client";

import { useState } from "react";
import { TableCell, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Prospect } from "@/types/leadgen";
import { formatCurrency, formatRelative } from "@/lib/leadgen-utils";
import ChannelBadge from "./ChannelBadge";
import { cn } from "@/lib/utils";

function ScoreBadge({ score }: { score?: number }) {
  if (score === undefined || score === null)
    return <span className="text-xs text-text-muted">—</span>;

  const cls =
    score <= 40
      ? "bg-red-100 text-red-700"
      : score <= 70
        ? "bg-yellow-100 text-yellow-700"
        : "bg-green-100 text-green-700";

  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-semibold", cls)}>
      {score}
    </span>
  );
}

interface ProspectRowProps {
  prospect: Prospect;
  onConfirm: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
}

export default function ProspectRow({
  prospect,
  onConfirm,
  onReject,
}: ProspectRowProps) {
  const [confirming, setConfirming] = useState(false);
  const [rejecting, setRejecting] = useState(false);

  async function handleConfirm() {
    setConfirming(true);
    try {
      await onConfirm(prospect.id);
    } finally {
      setConfirming(false);
    }
  }

  async function handleReject() {
    setRejecting(true);
    try {
      await onReject(prospect.id);
    } finally {
      setRejecting(false);
    }
  }

  const { name, debt_amount, channel, score } = prospect.qualification_data;

  return (
    <TableRow>
      <TableCell className="font-medium text-sm">
        {name ?? "Без имени"}
      </TableCell>
      <TableCell>
        {channel ? (
          <ChannelBadge channel={channel} />
        ) : (
          <span className="text-xs text-text-muted">—</span>
        )}
      </TableCell>
      <TableCell className="text-sm">
        {debt_amount !== undefined ? formatCurrency(debt_amount) : "—"}
      </TableCell>
      <TableCell>
        <ScoreBadge score={score} />
      </TableCell>
      <TableCell className="text-xs text-text-muted">
        {formatRelative(prospect.created_at)}
      </TableCell>
      <TableCell>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={confirming || rejecting}
            className="text-xs h-7 px-3"
            style={{ background: "#1D9E75", color: "#fff" }}
          >
            {confirming ? (
              <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              "Подтвердить"
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleReject}
            disabled={confirming || rejecting}
            className="text-xs h-7 px-3"
          >
            {rejecting ? (
              <span className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              "Отклонить"
            )}
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}
