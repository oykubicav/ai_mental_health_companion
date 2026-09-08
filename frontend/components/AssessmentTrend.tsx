"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { listAssessments } from "@/lib/api";
import { SEVERITY_LABELS_TR } from "@/lib/assessments";
import type { Assessment, AssessmentKind } from "@/lib/types";
import { Loader2, ArrowDown, ArrowUp, Minus } from "lucide-react";

interface Props {
  // Üyeliksiz kullanımda oturum kimliği; giriş yapılmışsa null
  // gönderilir ve sunucu kayıtları hesaba göre toplar.
  sessionId: string | null;
  kind: AssessmentKind;
}

// PHQ-9 severity threshold'ları — chart'ta çizgi olarak gösterilecek
const PHQ9_THRESHOLDS = [
  { value: 5, label: "hafif", color: "#eab308" },
  { value: 10, label: "orta", color: "#f97316" },
  { value: 15, label: "orta-şiddetli", color: "#ef4444" },
  { value: 20, label: "şiddetli", color: "#b91c1c" },
];

const GAD7_THRESHOLDS = [
  { value: 5, label: "hafif", color: "#eab308" },
  { value: 10, label: "orta", color: "#f97316" },
  { value: 15, label: "şiddetli", color: "#ef4444" },
];

export default function AssessmentTrend({ sessionId, kind }: Props) {
  const [data, setData] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const rows = await listAssessments(sessionId, kind, 20);
        if (!cancelled) setData(rows);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || "Sonuçlar yüklenirken bir hata oluştu.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId, kind]);

  const maxScore = kind === "phq9" ? 27 : 21;
  const thresholds = kind === "phq9" ? PHQ9_THRESHOLDS : GAD7_THRESHOLDS;

  // Chart data: recharts x-axis için tarih string'ini kısalt
  const chartData = data.map((a) => ({
    date: new Date(a.taken_at).toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "short",
    }),
    score: a.total_score,
    severity: SEVERITY_LABELS_TR[a.severity] ?? a.severity,
  }));

  // Loading state
  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <Loader2 className="animate-spin text-cbt-textMuted" size={20} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  // Empty state — henüz ölçüm yok
  if (data.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-cbt-textMuted">
          Henüz {kind === "phq9" ? "PHQ-9" : "GAD-7"} sonucun yok.
        </p>
        <p className="text-xs text-cbt-textMuted mt-2">
          İlk ölçümden sonra buradan zaman içindeki değişimi göreceksin.
        </p>
      </div>
    );
  }

  // Chart view
  return (
    <div className="w-full">
      <h3 className="text-sm font-medium text-cbt-text dark:text-cbt-dark-text mb-4">
        {kind === "phq9" ? "PHQ-9" : "GAD-7"} zaman içinde
      </h3>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
            />
            <YAxis
              domain={[0, maxScore]}
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
            />
            <Tooltip
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid #e5e7eb",
                fontSize: "12px",
              }}
              formatter={(value: number, _name: string, props: any) => [
                `${value}/${maxScore} · ${props.payload.severity}`,
                "Skor",
              ]}
            />

            {/* Severity threshold çizgileri */}
            {thresholds.map((t) => (
              <ReferenceLine
                key={t.value}
                y={t.value}
                stroke={t.color}
                strokeDasharray="3 3"
                strokeOpacity={0.4}
                label={{
                  value: t.label,
                  position: "right",
                  fill: t.color,
                  fontSize: 10,
                }}
              />
            ))}

            <Line
              type="monotone"
              dataKey="score"
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={{ r: 4, fill: "#0ea5e9" }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Summary text */}
      <div className="mt-4 flex items-center justify-between text-xs text-cbt-textMuted">
        <span>{data.length} ölçüm</span>
        {data.length >= 2 && <ChangeSummary data={data} />}
      </div>
    </div>
  );
}


/**
 * Son 2 ölçümdeki değişimi göster.
 * PHQ-9/GAD-7'de SKOR DÜŞMESİ = iyileşme, ARTIŞ = kötüleşme.
 */
function ChangeSummary({ data }: { data: Assessment[] }) {
  const previous = data[data.length - 2];
  const current = data[data.length - 1];
  const delta = current.total_score - previous.total_score;

  if (delta === 0) {
    return (
      <span className="flex items-center gap-1">
        <Minus size={12} />
        Değişim yok ({current.total_score})
      </span>
    );
  }

  if (delta < 0) {
    // Skor düştü → iyileşme
    return (
      <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
        <ArrowDown size={12} />
        {previous.total_score} → {current.total_score} (iyileşme)
      </span>
    );
  }

  // Skor arttı → kötüleşme
  return (
    <span className="flex items-center gap-1 text-orange-600 dark:text-orange-400">
      <ArrowUp size={12} />
      {previous.total_score} → {current.total_score} (artış)
    </span>
  );
}
