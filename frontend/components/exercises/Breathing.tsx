"use client";

import { useEffect, useRef, useState } from "react";
import { createExercise } from "@/lib/api";
import { useAuth } from "@/hooks/AuthProvider";
import PastEntries from "./PastEntries";
import type { BreathingPayload } from "@/lib/types";

// Ses yok, sayaç yok, "gün serisi" yok. Daire büyür, küçülür; bittiğinde
// bir cümle. Kartlardaki nefes tarifleriyle aynı süreler.
interface Mode {
  id: string;
  label: string;
  note: string;
  phases: { name: string; seconds: number; scale: number }[];
}

const MODES: Mode[] = [
  {
    id: "diaphragm",
    label: "Diyafram",
    note: "4 al, 6 ver. Panik ve hızlı nefes için; verirken uzatmak beden alarmını düşürür.",
    phases: [
      { name: "Al", seconds: 4, scale: 1 },
      { name: "Ver", seconds: 6, scale: 0.55 },
    ],
  },
  {
    id: "box",
    label: "Kutu",
    note: "4 al, 4 tut, 4 ver, 4 bekle. Toplantı öncesi, sınav anı gibi dikkat gereken yerlerde.",
    phases: [
      { name: "Al", seconds: 4, scale: 1 },
      { name: "Tut", seconds: 4, scale: 1 },
      { name: "Ver", seconds: 4, scale: 0.55 },
      { name: "Bekle", seconds: 4, scale: 0.55 },
    ],
  },
  {
    id: "478",
    label: "4-7-8",
    note: "4 al, 7 tut, 8 ver. Yatakta, uykuya geçerken. Başta baş dönmesi olursa normal nefese dön.",
    phases: [
      { name: "Al", seconds: 4, scale: 1 },
      { name: "Tut", seconds: 7, scale: 1 },
      { name: "Ver", seconds: 8, scale: 0.55 },
    ],
  },
];

const DURATIONS = [60, 180, 300];

export default function Breathing() {
  const { isAuthenticated } = useAuth();
  const [mode, setMode] = useState<Mode>(MODES[0]);
  const [duration, setDuration] = useState(180);
  const [running, setRunning] = useState(false);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [done, setDone] = useState<number | null>(null);
  const [saved, setSaved] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const timers = useRef<{ tick?: number; phase?: number }>({});

  function clear() {
    if (timers.current.tick) window.clearInterval(timers.current.tick);
    if (timers.current.phase) window.clearTimeout(timers.current.phase);
    timers.current = {};
  }

  function start() {
    clear();
    setDone(null);
    setSaved(false);
    setElapsed(0);
    setPhaseIdx(0);
    setRunning(true);
  }

  function stop(finished: boolean) {
    clear();
    setRunning(false);
    if (finished || elapsed >= 30) setDone(elapsed);
  }

  useEffect(() => {
    if (!running) return;
    timers.current.tick = window.setInterval(() => {
      setElapsed((e) => e + 1);
    }, 1000);
    return clear;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running]);

  useEffect(() => {
    if (!running) return;
    const p = mode.phases[phaseIdx];
    timers.current.phase = window.setTimeout(() => {
      setPhaseIdx((i) => (i + 1) % mode.phases.length);
    }, p.seconds * 1000);
    return () => {
      if (timers.current.phase) window.clearTimeout(timers.current.phase);
    };
  }, [running, phaseIdx, mode]);

  useEffect(() => {
    if (running && elapsed >= duration) stop(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elapsed, duration, running]);

  useEffect(() => clear, []);

  async function kaydet() {
    if (done === null || saved) return;
    const payload: BreathingPayload = { mode: mode.id, seconds: done };
    try {
      await createExercise("breathing", payload as unknown as Record<string, unknown>);
      setSaved(true);
      setRefreshKey((k) => k + 1);
    } catch {
      // kaydedilmedi; ekranda kalır
    }
  }

  const phase = mode.phases[phaseIdx];
  const kalan = Math.max(0, duration - elapsed);

  return (
    <div>
      {!running && done === null && (
        <div className="mb-10 space-y-6">
          <div>
            <div className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
              Ritim
            </div>
            <div className="flex flex-wrap gap-2">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setMode(m)}
                  className={
                    mode.id === m.id
                      ? "px-4 py-2 rounded-full text-[14px] font-medium bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg"
                      : "px-4 py-2 rounded-full text-[14px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text"
                  }
                >
                  {m.label}
                </button>
              ))}
            </div>
            <p className="mt-3 text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
              {mode.note}
            </p>
          </div>

          <div>
            <div className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
              Süre
            </div>
            <div className="flex gap-2">
              {DURATIONS.map((d) => (
                <button
                  key={d}
                  onClick={() => setDuration(d)}
                  className={
                    duration === d
                      ? "px-4 py-2 rounded-full text-[14px] font-medium bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg"
                      : "px-4 py-2 rounded-full text-[14px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary"
                  }
                >
                  {d / 60} dk
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="relative flex flex-col items-center justify-center py-10 select-none">
        <div className="relative w-64 h-64 flex items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-cbt-border dark:border-cbt-dark-border" />
          <div
            className="absolute rounded-full bg-cbt-accentSoft dark:bg-cbt-dark-accentSoft"
            style={{
              width: 256,
              height: 256,
              transform: `scale(${running ? phase.scale : 0.55})`,
              transition: running
                ? `transform ${phase.seconds}s cubic-bezier(0.45, 0, 0.55, 1)`
                : "transform 600ms ease",
            }}
          />
          <div
            className="absolute rounded-full bg-cbt-accent dark:bg-cbt-dark-accent opacity-90"
            style={{
              width: 256,
              height: 256,
              transform: `scale(${running ? phase.scale * 0.72 : 0.4})`,
              transition: running
                ? `transform ${phase.seconds}s cubic-bezier(0.45, 0, 0.55, 1)`
                : "transform 600ms ease",
            }}
          />
          <div className="relative text-center">
            {running ? (
              <>
                <div className="display text-[34px] leading-none text-white">{phase.name}</div>
                <div className="mt-1 text-[12px] text-white/80 tabular-nums">{phase.seconds} sn</div>
              </>
            ) : done !== null ? (
              <div className="display text-[22px] text-white">Bitti.</div>
            ) : (
              <button
                onClick={start}
                className="display text-[26px] text-white hover:opacity-90 transition-opacity"
              >
                Başla
              </button>
            )}
          </div>
        </div>

        {running && (
          <div className="mt-8 flex items-center gap-6">
            <span className="text-[13px] tabular-nums text-cbt-textMuted dark:text-cbt-dark-textMuted">
              {Math.floor(kalan / 60)}:{String(kalan % 60).padStart(2, "0")}
            </span>
            <button
              onClick={() => stop(false)}
              className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text"
            >
              Bitir
            </button>
          </div>
        )}
      </div>

      {done !== null && (
        <div className="animate-slide-up mt-2 p-6 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60">
          <p className="text-[15px] text-cbt-text dark:text-cbt-dark-text leading-relaxed">
            {Math.round(done / 60) || 1} dakika {mode.label.toLowerCase()} nefesi. Şu an bedenin
            nasıl, bir saniye fark et — daha sakin olmak zorunda değil, olduğu gibi.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              onClick={start}
              className="px-5 h-10 rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85"
            >
              Bir daha
            </button>
            {isAuthenticated && !saved && (
              <button
                onClick={kaydet}
                className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text"
              >
                Kaydet
              </button>
            )}
            {saved && (
              <span className="text-[13px] text-cbt-success dark:text-cbt-dark-success">Kaydedildi</span>
            )}
            <button
              onClick={() => setDone(null)}
              className="text-[14px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text"
            >
              Ayarlar
            </button>
          </div>
        </div>
      )}

      <PastEntries
        kind="breathing"
        refreshKey={refreshKey}
        render={(e) => {
          const p = e.payload as unknown as BreathingPayload;
          const m = MODES.find((x) => x.id === p.mode);
          return (
            <p className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
              {m?.label ?? p.mode} · {Math.round(p.seconds / 60) || 1} dk
            </p>
          );
        }}
      />
    </div>
  );
}
