"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { LayoutGrid, Trash2, Send, Bug, HelpCircle, Wind, NotebookPen } from "lucide-react";
import { postChat, deleteSession,getMySession } from "@/lib/api";
import { getSessionId, setSessionId, clearSessionId } from "@/lib/session";
import type { Turn } from "@/lib/types";
import Message from "./Message";
import ThemeToggle from "./ThemeToggle";
import SuggestedPrompts from "./SuggestedPrompts";
import Link from "next/link";
import { LineChart } from "lucide-react";
import { shouldPromptNow } from "@/lib/assessments";
import AssessmentReminderBanner from "./AssessmentReminderBanner";
import TransparencyPanel from "./TransparencyPanel";
import SessionHandoff from "./SessionHandoff";
import CrisisConfirm from "./CrisisConfirm";
import { useAuth } from "@/hooks/AuthProvider";
import { LogIn, LogOut, User } from "lucide-react";
import { History } from "lucide-react";
import HistoryPanel from "./HistoryPanel";
import { focusLabelsFor, clearProfile } from "@/lib/profile";

function buildWelcome(name: string, focusLabels: string[], inTherapy = false): string {
  const greeting = name ? `Merhaba ${name}.` : "Merhaba, hoş geldin.";
  // Konular gibi yalnızca ilk sohbette söylenir (aynı damga).
  const therapyNote = inTherapy
    ? " Bir uzmanla görüştüğünü söylemiştin; burada fark ettiklerini oraya taşımak iyi olabilir, ben onun yerine değil yanına geliyorum."
    : "";

  if (focusLabels.length === 0) {
    return `${greeting}${therapyNote} Bugün nasıl gidiyor? Aklından geçen neyse anlatabilirsin.`;
  }

  const topics =
    focusLabels.length === 1
      ? focusLabels[0].toLowerCase()
      : focusLabels.slice(0, -1).join(", ").toLowerCase() +
        " ve " +
        focusLabels[focusLabels.length - 1].toLowerCase();

  return `${greeting}${therapyNote} Başlarken ${topics} demiştin. İstersen oradan başlayalım, istersen bugün aklında ne varsa onu anlat. Acelemiz yok.`;
}

export default function ChatWindow() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSid] = useState<string>("");
  const [showDebug, setShowDebug] = useState(false);
  const [welcome, setWelcome] = useState(
    "Merhaba, hoş geldin. Bugün seni buraya getiren ne? Anlatmak istediğin neyse dinliyorum."
  );
  const [boundary, setBoundary] = useState("normal");
  const [handoffDismissed, setHandoffDismissed] = useState(false);
  const [deniedTurns, setDeniedTurns] = useState<Set<string>>(new Set());
  const [historyOpen, setHistoryOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [transparencyTurnId, setTransparencyTurnId] = useState<string | null>(null);
  const { user, isAuthenticated, logout, updateProfile } = useAuth();

  useEffect(() => {
    const saved = getSessionId();
    if (saved) setSid(saved);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns.length, pending]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const send = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || pending) return;
    setPending(true);
    setError(null);
    setInput("");
    setSending(trimmed);
    textareaRef.current?.focus();
    try {
      const res = await postChat({
        user_message: trimmed,
        session_id: sessionId || undefined,
      });
      if (res.session_id !== sessionId) {
        setSid(res.session_id);
        setSessionId(res.session_id);
      }
      setTurns((prev) => [
        ...prev,
        { user_message: trimmed, chat: res, ts: Date.now() },
      ]);
      setBoundary(res.boundary_state || "normal");
      setSending(null);
    } catch (e: any) {
      setError(e?.message || "Bir hata oluştu.");
      setSending(null);
      setInput(trimmed);
    } finally {
      setPending(false);
    }
  }, [input, pending, sessionId]);

  const handleFeedback = (turnId: string, verdict: Turn["feedback_sent"]) => {
    setTurns((prev) =>
      prev.map((t) =>
        t.chat.turn_id === turnId ? { ...t, feedback_sent: verdict } : t
      )
    );
  };

  const resetSession = async () => {
    if (!confirm("Bu oturumu ve tüm mesajlarını silmek istediğine emin misin?")) {
      return;
    }
    if (sessionId) {
      try {
        await deleteSession(sessionId);
      } catch {
        /* non-fatal */
      }
    }
    clearSessionId();
    clearProfile();
    setSid("");
    setTurns([]);
    setError(null);
    window.location.href = "/";
  };
  // Kullanıcı kontrol sorusunu onayladı: tam kriz yanıtı istenir.
  // Kontrol sorusuna verilen yanıt her iki durumda da geçmişe yazılır; aksi
  // hâlde konuşmada cevapsız bir soru kalır ve sonraki turda bağlam bozulur.
  const answerCrisisCheck = async (turnId: string, confirmed: boolean) => {
    const text = confirmed ? "Evet, öyle." : "Hayır, öyle değil.";
    setDeniedTurns((prev) => new Set(prev).add(turnId));
    setPending(true);
    setError(null);
    try {
      const res = await postChat({
        user_message: text,
        session_id: sessionId || undefined,
        ...(confirmed ? { crisis_confirmed: true } : {}),
      });
      setTurns((prev) => [
        ...prev,
        { user_message: text, chat: res, ts: Date.now() },
      ]);
    } catch (e: any) {
      setError(e?.message || "Bir hata oluştu.");
    } finally {
      setPending(false);
      textareaRef.current?.focus();
    }
  };

  const startFreshSession = async () => {
    clearSessionId();
    setSid("");
    setTurns([]);
    setBoundary("normal");
    setHandoffDismissed(false);
    setError(null);
    setWelcome(
      user?.display_name
        ? `Yeni bir sayfa açtık ${user.display_name}. Konuştuklarımız aklımda — bugün kaldığımız yerden devam edebiliriz, istersen başka bir şeyle başlayabilirsin.`
        : "Yeni bir sayfa açtık. Konuştuklarımız aklımda — kaldığımız yerden devam edebiliriz, istersen başka bir şeyle başlayabilirsin."
    );
    textareaRef.current?.focus();
  };
    const openSession = async (id: string) => {
    setHistoryOpen(false);
    setError(null);
    setPending(true);
    try {
      const detail = await getMySession(id);
      const loaded: Turn[] = detail.turns.map((t) => ({
        user_message: t.user_message ?? "",
        ts: new Date(t.ts).getTime(),
        chat: {
          turn_id: t.turn_id,
          session_id: detail.session_id,
          response: t.response,
          safety: {
            route: "cbt_support",
            allow_cbt: true,
            highest_risk: "low",
            matched_card_ids: [],
          },
          intent: { module: "unknown", subintent: "unknown", confidence: 0 },
          retrieved_card_ids: [],
          critic: { passed: true, rewrites: 0, used_fallback: false },
          timing_ms: {},
        },
      }));
      setTurns(loaded);
      setSid(detail.session_id);
      setSessionId(detail.session_id);
      setHandoffDismissed(false);
      setBoundary("normal");
    } catch {
      setError("Sohbet yüklenemedi.");
    } finally {
      setPending(false);
    }
  };

  // Ölçüm hatırlatması yalnızca hesabı olanlara — anonim oturumda geçmiş
  // saklanmadığı için "bu haftaki ölçüm" ifadesinin karşılığı yok.
  const [showBanner, setShowBanner] = useState(false);
  useEffect(() => {
    setShowBanner(isAuthenticated && shouldPromptNow());
  }, [isAuthenticated]);

  // Karşılama, kullanıcı bilgisi geldiğinde bir kez kurulur. Ad her sohbette
  // anılır; onboarding'de seçilen konular yalnızca ilk sohbette — sunucudaki
  // focus_greeted_at damgası bunu taşıyor.
  const welcomeBuilt = useRef(false);
  useEffect(() => {
    if (!user || welcomeBuilt.current) return;
    welcomeBuilt.current = true;

    const first = !user.focus_greeted_at;
    const labels = first ? focusLabelsFor(user.focus_topics) : [];
    const inTherapy = first && user.therapy_experience === "ongoing";
    setWelcome(buildWelcome(user.display_name ?? "", labels, inTherapy));

    if (labels.length > 0 || inTherapy) {
      void updateProfile({ focus_greeted: true }).catch(() => {});
    }
  }, [user, updateProfile]);

  return (
    <div className="flex flex-col h-screen max-h-screen bg-cbt-bg dark:bg-cbt-dark-bg">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-cbt-border/60 dark:border-cbt-dark-border/60 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl backdrop-saturate-150">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-3 px-4 py-3">
          <div>
            <h1 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text">
              Neva
            </h1>
            <p className="text-xs text-cbt-textMuted dark:text-cbt-dark-textMuted mt-0.5">
              Bilişsel davranışçı terapi tabanlı destek
            </p>
          </div>
          <div className="flex items-center gap-1">
            {process.env.NODE_ENV !== "production" && (
              <IconButton
                label="Debug"
                active={showDebug}
                onClick={() => setShowDebug((v) => !v)}
              >
                <Bug size={16} strokeWidth={2.2} />
              </IconButton>
            )}
              {isAuthenticated && (
              <IconButton label="Sohbetlerim" onClick={() => setHistoryOpen(true)}>
                <History size={16} strokeWidth={2.2} />
              </IconButton>
            )}
            <IconButton label="Konular" href="/cards">
              <LayoutGrid size={16} strokeWidth={2.2} />
            </IconButton>
            <IconButton label="Egzersizler" href="/egzersizler">
              <Wind size={16} strokeWidth={2.2} />
            </IconButton>
            {isAuthenticated && (
              <IconButton label="Günlük" href="/gunluk">
                <NotebookPen size={16} strokeWidth={2.2} />
              </IconButton>
            )}
            <Link
            href="/progress"
            className="text-sm text-cbt-textSecondary hover:text-cbt-text flex items-center gap-1"
            >
            <LineChart size={14} />
            Gelişimim
            </Link>
            <ThemeToggle />
            <IconButton label="Oturumu sil" danger onClick={resetSession}>
              <Trash2 size={16} strokeWidth={2.2} />
            </IconButton>
            {isAuthenticated ? (
  <div className="flex items-center gap-2">
    
    <IconButton label="Hesabım" href="/hesabim">
      <User size={16} strokeWidth={2.2} />
    </IconButton>
    <IconButton label="Çıkış yap" onClick={() => {
      logout();
    }}>
      <LogOut size={16} strokeWidth={2.2} />
    </IconButton>
  </div>
) : (
  <Link
    href="/login"
    className="flex items-center gap-1 text-sm text-cbt-accent hover:text-cbt-accent/80"
  >
    <LogIn size={14} />
    <span>Giriş</span>
  </Link>
)}

            
          </div>
        </div>
      </header>
      {showBanner && (
  <AssessmentReminderBanner onDismiss={() => setShowBanner(false)} />
)}
      

      {/* Messages */}
      <div ref={scrollRef} className="chat-scroll flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-[85%] rounded-2xl bg-cbt-assistantBubble dark:bg-cbt-dark-assistantBubble px-5 py-4 shadow-soft border border-cbt-border/40 dark:border-cbt-dark-border/40">
              <p className="text-[15px] text-cbt-text dark:text-cbt-dark-text leading-[1.55]">
                {welcome}
              </p>
            </div>
          </div>

          {/* Suggested prompts — only when no turns yet */}
          {turns.length === 0 && !pending && (
            <div className="pl-1 pt-2">
              <SuggestedPrompts
                onPick={(prompt) => {
                  setInput(prompt);
                  textareaRef.current?.focus();
                }}
              />
            </div>
          )}

          {turns.map((t) => (
            <div key={t.chat.turn_id}>
              <Message
                turn={t}
                sessionId={sessionId}
                onFeedbackSent={handleFeedback}
                showDebug={showDebug}
              />
              {t.chat.safety?.needs_confirmation && !deniedTurns.has(t.chat.turn_id) && (
                <div className="mt-3">
                  <CrisisConfirm
                    onConfirm={() => answerCrisisCheck(t.chat.turn_id, true)}
                    onDeny={() => answerCrisisCheck(t.chat.turn_id, false)}
                  />
                </div>
              )}
              <div className="flex justify-start mt-1 pl-2">
                <button
                  onClick={() => setTransparencyTurnId(t.chat.turn_id)}
                  className="text-[11px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-accent dark:hover:text-cbt-dark-accent inline-flex items-center gap-1 transition-colors"
                  aria-label="Bu cevap nasıl üretildi"
                >
                  <HelpCircle size={11} />
                  nasıl üretildi
                </button>
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-end animate-fade-in">
              <div className="max-w-[85%] rounded-2xl bg-cbt-userBubble dark:bg-cbt-dark-userBubble px-5 py-3.5">
                <p className="text-[15px] text-cbt-userBubbleText dark:text-cbt-dark-userBubbleText leading-[1.55] whitespace-pre-wrap">
                  {sending}
                </p>
              </div>
            </div>
          )}

          {pending && (
            <div className="flex justify-start animate-fade-in">
              <div className="max-w-[85%] rounded-2xl bg-cbt-assistantBubble dark:bg-cbt-dark-assistantBubble px-5 py-4 shadow-soft border border-cbt-border/40 dark:border-cbt-dark-border/40">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          )}

          {boundary === "hard_close" && !pending && !handoffDismissed && sessionId && (
            <SessionHandoff
              sessionId={sessionId}
              onStartNew={startFreshSession}
              onDismiss={() => setHandoffDismissed(true)}
            />
          )}

          {error && (
            <div className="text-xs text-cbt-danger dark:text-cbt-dark-danger bg-cbt-dangerSoft dark:bg-cbt-dark-dangerSoft border border-cbt-danger/20 dark:border-cbt-dark-danger/30 rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          <div className="h-4" />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-cbt-border/60 dark:border-cbt-dark-border/60 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl backdrop-saturate-150 px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-2 bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border rounded-2xl px-3 py-2 shadow-subtle focus-within:border-cbt-borderStrong dark:focus-within:border-cbt-dark-borderStrong transition-colors">
            <textarea
              ref={textareaRef}
              className="flex-1 resize-none bg-transparent text-[15px] px-1 py-1.5 focus:outline-none placeholder:text-cbt-textMuted dark:placeholder:text-cbt-dark-textMuted text-cbt-text dark:text-cbt-dark-text min-h-[24px] max-h-40 leading-[1.5]"
              placeholder="Mesajını yaz…"
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, 4000))}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              disabled={pending}
              rows={1}
            />
            <button
              className="flex items-center justify-center w-9 h-9 rounded-full bg-cbt-accent dark:bg-cbt-dark-accent text-white dark:text-cbt-dark-bg hover:bg-cbt-accentHover dark:hover:bg-cbt-dark-accentHover disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
              onClick={send}
              disabled={pending || !input.trim()}
              aria-label="Gönder"
            >
              <Send size={15} strokeWidth={2.4} />
            </button>
          </div>
          <div className="mt-2 flex justify-between items-center text-[11px] text-cbt-textMuted dark:text-cbt-dark-textMuted px-1">
            <span>
              Neva bir terapist değildir. Acil bir durumdaysan{" "}
              <span className="font-medium text-cbt-text dark:text-cbt-dark-text">112</span>'yi ara.
            </span>
            <span
              className={
                input.length > 3500
                  ? "text-cbt-warning dark:text-cbt-dark-warning"
                  : ""
              }
            >
              {input.length}/4000
            </span>
          </div>
        </div>
      </div>

      {/* Transparency modal — sadece açık olduğunda render */}
      {transparencyTurnId && (
        <TransparencyPanel
          turnId={transparencyTurnId}
          onClose={() => setTransparencyTurnId(null)}
        />
      )}
      <HistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        activeSessionId={sessionId}
        onSelect={openSession}
      />
    </div>
  );
}

function IconButton({
  children,
  label,
  onClick,
  href,
  active,
  danger,
}: {
  children: React.ReactNode;
  label: string;
  onClick?: () => void;
  href?: string;
  active?: boolean;
  danger?: boolean;
}) {
  const cls = [
    "flex items-center justify-center w-8 h-8 rounded-lg transition-colors",
    active
      ? "bg-cbt-accent/15 text-cbt-accent dark:bg-cbt-dark-accent/20 dark:text-cbt-dark-accent"
      : danger
      ? "text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-danger dark:hover:text-cbt-dark-danger hover:bg-cbt-dangerSoft dark:hover:bg-cbt-dark-dangerSoft"
      : "text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text hover:bg-cbt-surfaceMuted dark:hover:bg-cbt-dark-surfaceMuted",
  ].join(" ");
  if (href) {
    return (
      <a href={href} className={cls} title={label} aria-label={label}>
        {children}
      </a>
    );
  }
  return (
    <button onClick={onClick} className={cls} title={label} aria-label={label}>
      {children}
    </button>
  );
}
