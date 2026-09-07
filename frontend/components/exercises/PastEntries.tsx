"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { listExercises, deleteExercise } from "@/lib/api";
import { useAuth } from "@/hooks/AuthProvider";
import type { ExerciseEntry, ExerciseKind } from "@/lib/types";

export function tarih(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

// Hesabı olan kullanıcının bu araçtaki eski kayıtları. Anonim kullanıcıya
// hiçbir şey göstermez; sayfa yine çalışır.
export default function PastEntries({
  kind,
  refreshKey,
  render,
}: {
  kind: ExerciseKind;
  refreshKey: number;
  render: (entry: ExerciseEntry) => React.ReactNode;
}) {
  const { isAuthenticated } = useAuth();
  const [entries, setEntries] = useState<ExerciseEntry[]>([]);

  const load = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const r = await listExercises(kind);
      setEntries(r.entries);
    } catch {
      setEntries([]);
    }
  }, [isAuthenticated, kind]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  async function sil(id: string) {
    try {
      await deleteExercise(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch {
      // liste olduğu gibi kalır
    }
  }

  if (!isAuthenticated || entries.length === 0) return null;

  return (
    <section className="mt-14">
      <h2 className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-4">
        Öncekiler
      </h2>
      <ul className="space-y-3">
        {entries.map((e) => (
          <li
            key={e.id}
            className="group relative p-5 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60"
          >
            <div className="display text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted mb-2">
              {tarih(e.created_at)}
            </div>
            {render(e)}
            <button
              onClick={() => sil(e.id)}
              aria-label="Sil"
              className="absolute top-4 right-4 p-1.5 rounded-lg text-cbt-textMuted dark:text-cbt-dark-textMuted opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-all"
            >
              <Trash2 size={14} />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
