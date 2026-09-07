"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Check, Trash2 } from "lucide-react";
import { saveJournalDay, deleteJournalDay } from "@/lib/api";
import {
  JOURNAL_TAGS,
  MOODS,
  bugun,
  gunBasligi,
  gunKaydir,
} from "@/lib/journal";
import type { JournalEntry } from "@/lib/types";

// Tek günün kartı. Yazdıkça kısa bir gecikmeyle kaydediliyor; "kaydet"
// düğmesine basmayı unutan kullanıcı yazdığını kaybetmesin.
//
// Sayfa bunu key={date} ile kuruyor: gün değişince bileşen sıfırdan
// kuruluyor, o yüzden içeride "günü yeniden yükle" etkisi yok. Kayıt
// sonrası gelen prop güncellemesi formu ezmiyor.

const AUTOSAVE_MS = 900;

interface Props {
  date: string;
  entry: JournalEntry | null;
  onSaved: (entry: JournalEntry) => void;
  onDeleted: (date: string) => void;
  onNavigate: (date: string) => void;
}

export default function JournalDay({ date, entry, onSaved, onDeleted, onNavigate }: Props) {
  const [mood, setMood] = useState<number | null>(entry?.mood ?? null);
  const [did, setDid] = useState(entry?.did ?? "");
  const [thoughts, setThoughts] = useState(entry?.thoughts ?? "");
  const [good, setGood] = useState(entry?.good ?? "");
  const [tags, setTags] = useState<string[]>(entry?.tags ?? []);
  const [durum, setDurum] = useState<"bos" | "yaziliyor" | "kaydedildi" | "hata">(
    entry ? "kaydedildi" : "bos"
  );
  const [silinecek, setSilinecek] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const ilkYukleme = useRef(true);

  const kaydet = useCallback(async () => {
    setDurum("yaziliyor");
    try {
      const kayit = await saveJournalDay(date, {
        mood: mood ?? undefined,
        did,
        thoughts,
        good,
        tags,
      });
      setDurum("kaydedildi");
      onSaved(kayit);
    } catch {
      setDurum("hata");
    }
  }, [date, mood, did, thoughts, good, tags, onSaved]);

  useEffect(() => {
    if (ilkYukleme.current) {
      ilkYukleme.current = false;
      return;
    }
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void kaydet(), AUTOSAVE_MS);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [mood, did, thoughts, good, tags, kaydet]);

  async function sil() {
    try {
      await deleteJournalDay(date);
      onDeleted(date);
    } finally {
      setSilinecek(false);
    }
  }

  const ileriKapali = date >= bugun();

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={() => onNavigate(gunKaydir(date, -1))}
          aria-label="Önceki gün"
          className="w-9 h-9 flex items-center justify-center rounded-full border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
        >
          <ChevronLeft size={16} strokeWidth={2} />
        </button>

        <div className="text-center">
          <div className="display text-[26px] sm:text-[30px] leading-none text-cbt-text dark:text-cbt-dark-text">
            {gunBasligi(date)}
          </div>
          <div className="mt-1.5 h-4 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
            {durum === "yaziliyor" && "Kaydediliyor…"}
            {durum === "kaydedildi" && (
              <span className="inline-flex items-center gap-1 text-cbt-success dark:text-cbt-dark-success">
                <Check size={11} strokeWidth={3} />
                Kaydedildi
              </span>
            )}
            {durum === "hata" && (
              <span className="text-cbt-danger dark:text-cbt-dark-danger">Kaydedilemedi</span>
            )}
          </div>
        </div>

        <button
          onClick={() => onNavigate(gunKaydir(date, 1))}
          disabled={ileriKapali}
          aria-label="Sonraki gün"
          className="w-9 h-9 flex items-center justify-center rounded-full border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text disabled:opacity-25 disabled:hover:text-cbt-textSecondary transition-colors"
        >
          <ChevronRight size={16} strokeWidth={2} />
        </button>
      </div>

      <section className="mb-10">
        <Label>Gün nasıldı?</Label>
        <div className="flex gap-2">
          {MOODS.map((m) => (
            <button
              key={m.value}
              onClick={() => setMood(mood === m.value ? null : m.value)}
              className={`flex-1 py-3 rounded-2xl border text-[13px] transition-all active:scale-[0.98] ${
                mood === m.value
                  ? "border-transparent bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg font-medium"
                  : "border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <Label>Bugün ne oldu, ne yaptın?</Label>
        <Area
          value={did}
          onChange={setDid}
          placeholder="Sıradan şeyler de sayılır: kalktım, işe gittim, akşam yürüdüm…"
        />
      </section>

      <section className="mb-10">
        <Label>Aklından neler geçti?</Label>
        <Area
          value={thoughts}
          onChange={setThoughts}
          placeholder="Kafanı en çok meşgul eden düşünce neydi? Düzgün cümle gerekmiyor."
        />
      </section>

      <section className="mb-10">
        <Label>İyi gelen bir şey</Label>
        <Area
          value={good}
          onChange={setGood}
          rows={2}
          placeholder="Küçük olabilir. Bulamadıysan boş bırak — her günün olmak zorunda değil."
        />
      </section>

      <section className="mb-10">
        <Label>Etiketler</Label>
        <div className="flex flex-wrap gap-2">
          {JOURNAL_TAGS.map((t) => {
            const secili = tags.includes(t.id);
            return (
              <button
                key={t.id}
                onClick={() =>
                  setTags((prev) =>
                    prev.includes(t.id) ? prev.filter((x) => x !== t.id) : [...prev, t.id].slice(0, 6)
                  )
                }
                className={`px-3.5 py-2 rounded-full text-[13px] border transition-all active:scale-[0.98] ${
                  secili
                    ? "border-transparent bg-cbt-accentSoft dark:bg-cbt-dark-accentSoft text-cbt-accent dark:text-cbt-dark-accent font-medium"
                    : "border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
          En fazla altı tane. Yazacak vaktin yoksa yalnızca bunlara dokunup çıkabilirsin.
        </p>
      </section>

      {entry && (
        <div className="pt-5 border-t border-cbt-border/50 dark:border-cbt-dark-border/50">
          {silinecek ? (
            <div className="flex items-center gap-3">
              <button
                onClick={sil}
                className="text-[13px] px-3 py-1.5 rounded-lg bg-cbt-danger/10 text-cbt-danger dark:text-cbt-dark-danger"
              >
                Evet, bu günü sil
              </button>
              <button
                onClick={() => setSilinecek(false)}
                className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted"
              >
                Vazgeç
              </button>
            </div>
          ) : (
            <button
              onClick={() => setSilinecek(true)}
              className="inline-flex items-center gap-1.5 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-colors"
            >
              <Trash2 size={12} />
              Bu günü sil
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text mb-3">{children}</h2>
  );
}

function Area({
  value,
  onChange,
  placeholder,
  rows = 3,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  rows?: number;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value.slice(0, 2000))}
      placeholder={placeholder}
      rows={rows}
      className="w-full px-5 py-4 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[16px] leading-relaxed text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted/70 focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong resize-none transition-colors"
    />
  );
}
