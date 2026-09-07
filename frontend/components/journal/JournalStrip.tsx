"use client";

import { sonGunler, kisaTarih, bugun } from "@/lib/journal";
import type { JournalEntry } from "@/lib/types";

// Son iki hafta. Dolu günler renkli, boş günler boş — ama boşluk bir
// eksik değil: seri, yüzde ya da "kaçırdın" yok.

const MOOD_TONE: Record<number, string> = {
  1: "bg-cbt-warning/70 dark:bg-cbt-dark-warning/70",
  2: "bg-cbt-warning/45 dark:bg-cbt-dark-warning/45",
  3: "bg-cbt-accent/40 dark:bg-cbt-dark-accent/40",
  4: "bg-cbt-accent/65 dark:bg-cbt-dark-accent/65",
  5: "bg-cbt-accent dark:bg-cbt-dark-accent",
};

const GUN_HARFI = ["P", "S", "Ç", "P", "C", "C", "P"];

export default function JournalStrip({
  entries,
  selected,
  onSelect,
}: {
  entries: Record<string, JournalEntry>;
  selected: string;
  onSelect: (date: string) => void;
}) {
  const gunler = sonGunler(14);

  return (
    <div>
      <div className="flex gap-1.5 sm:gap-2">
        {gunler.map((g) => {
          const kayit = entries[g];
          const secili = g === selected;
          const [y, m, d] = g.split("-").map(Number);
          const haftaGunu = (new Date(y, m - 1, d).getDay() + 6) % 7;

          const doluTon = kayit
            ? kayit.mood
              ? MOOD_TONE[kayit.mood]
              : "bg-cbt-borderStrong dark:bg-cbt-dark-borderStrong"
            : "bg-transparent";

          return (
            <button
              key={g}
              onClick={() => onSelect(g)}
              title={`${kisaTarih(g)}${kayit ? "" : " — kayıt yok"}`}
              className="flex-1 group"
            >
              <span
                className={`block h-10 sm:h-12 rounded-lg border transition-all ${doluTon} ${
                  secili
                    ? "border-cbt-text dark:border-cbt-dark-text"
                    : kayit
                      ? "border-transparent group-hover:border-cbt-borderStrong dark:group-hover:border-cbt-dark-borderStrong"
                      : "border-cbt-border dark:border-cbt-dark-border border-dashed group-hover:border-cbt-borderStrong dark:group-hover:border-cbt-dark-borderStrong"
                }`}
              />
              <span
                className={`block mt-1.5 text-[10px] tabular-nums ${
                  secili
                    ? "text-cbt-text dark:text-cbt-dark-text font-medium"
                    : "text-cbt-textMuted dark:text-cbt-dark-textMuted"
                }`}
              >
                {g === bugun() ? "bugün" : GUN_HARFI[haftaGunu]}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
