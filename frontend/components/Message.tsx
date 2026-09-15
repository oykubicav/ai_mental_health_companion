"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowUpRight } from "lucide-react";
import type { Turn } from "@/lib/types";
import { formatRelativeTime } from "@/lib/time";
import DebugPanel from "./DebugPanel";
import FeedbackButtons from "./FeedbackButtons";
import { exerciseLinkFor } from "@/lib/exerciseLinks";

export default function Message({
  turn,
  sessionId,
  onFeedbackSent,
  showDebug,
}: {
  turn: Turn;
  sessionId: string;
  onFeedbackSent: (
    turnId: string,
    verdict: "thumbs_up" | "thumbs_down" | "flag"
  ) => void;
  showDebug: boolean;
}) {
  const isSafetyResponse = !turn.chat.safety.allow_cbt;
  const [tick, setTick] = useState(0);

  // Refresh relative timestamp every 30s
  useEffect(() => {
    if (!turn.ts) return;
    const id = setInterval(() => setTick((v) => v + 1), 30000);
    return () => clearInterval(id);
  }, [turn.ts]);

  // Cevapta kullanılan kartın bir aracı varsa altına bağlantı koyulur.
  // Kriz ve egzersizsiz destek yollarında çıkmaz.
  const exerciseLink = exerciseLinkFor(turn.chat.retrieved_card_ids, {
    allowCbt: turn.chat.safety.allow_cbt,
    blocksExercise: turn.chat.safety.blocks_exercise,
    conversationState: turn.chat.intent?.conversation_state,
  });

  return (
    <div className="space-y-3 animate-slide-up group/msg">
      {/* User bubble */}
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-2xl bg-cbt-userBubble dark:bg-cbt-dark-userBubble text-cbt-userBubbleText dark:text-cbt-dark-userBubbleText px-4 py-2.5 text-[15px] whitespace-pre-wrap leading-relaxed">
          {turn.user_message}
        </div>
      </div>

      {/* Assistant bubble */}
      <div className="flex justify-start">
        <div className="max-w-[85%] rounded-2xl bg-cbt-assistantBubble dark:bg-cbt-dark-assistantBubble px-5 py-4 shadow-soft border border-cbt-border/40 dark:border-cbt-dark-border/40">
          {isSafetyResponse && (
            <div className="mb-3 flex items-start gap-2 px-3 py-2 rounded-lg bg-cbt-dangerSoft dark:bg-cbt-dark-dangerSoft border border-cbt-danger/20 dark:border-cbt-dark-danger/30">
              <AlertTriangle
                size={14}
                className="text-cbt-danger dark:text-cbt-dark-danger flex-shrink-0 mt-0.5"
                strokeWidth={2.2}
              />
              <p className="text-xs text-cbt-danger dark:text-cbt-dark-danger leading-relaxed">
                Bu yanıt güvenlik yönlendirmesi içeriyor. Lütfen alttaki uzman
                bilgilerini dikkate al.
              </p>
            </div>
          )}
          <div className="text-[15px] text-cbt-text dark:text-cbt-dark-text whitespace-pre-wrap leading-[1.55]">
            {turn.chat.response}
          </div>
          {exerciseLink && (
            <Link
              href={exerciseLink.href}
              className="mt-3.5 flex items-center justify-between gap-3 px-4 py-3 rounded-xl bg-cbt-surfaceMuted dark:bg-cbt-dark-surfaceMuted hover:bg-cbt-accentSoft dark:hover:bg-cbt-dark-accentSoft transition-colors group/ex"
            >
              <span className="min-w-0">
                <span className="block text-[14px] font-medium text-cbt-text dark:text-cbt-dark-text">
                  {exerciseLink.label}
                </span>
                <span className="block text-[12px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                  {exerciseLink.note}
                </span>
              </span>
              <ArrowUpRight
                size={16}
                strokeWidth={2}
                className="shrink-0 text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover/ex:text-cbt-accent dark:group-hover/ex:text-cbt-dark-accent transition-colors"
              />
            </Link>
          )}
          <FeedbackButtons
            turnId={turn.chat.turn_id}
            sessionId={sessionId}
            sent={turn.feedback_sent}
            onSent={(v) => onFeedbackSent(turn.chat.turn_id, v)}
          />
          {showDebug && <DebugPanel turn={turn.chat} />}
        </div>
      </div>

      {/* Timestamp — appears on hover of message row, subtle */}
      {turn.ts && (
        <div
          className="text-[10.5px] text-cbt-textMuted dark:text-cbt-dark-textMuted opacity-0 group-hover/msg:opacity-100 transition-opacity pl-2"
          suppressHydrationWarning
        >
          {formatRelativeTime(turn.ts)}
        </div>
      )}
    </div>
  );
}
