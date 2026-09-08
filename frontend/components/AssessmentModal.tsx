"use client";

import { useState } from "react";
import { submitAssessment } from "@/lib/api";
import {
  PHQ9_QUESTIONS_TR, GAD7_QUESTIONS_TR,
  LIKERT_OPTIONS_TR, SEVERITY_LABELS_TR, SEVERITY_COLORS,
  markAssessmentTaken,
} from "@/lib/assessments";
import type { AssessmentKind, AssessmentSubmitResponse } from "@/lib/types";
import { AlertTriangle, X, ChevronRight } from "lucide-react";

interface Props {
  // Üyeliksiz kullanımda oturum kimliği; girişli kullanıcıda null.
  sessionId: string | null;
  kind: AssessmentKind;
  onClose: () => void;
  onSubmit?: (resp: AssessmentSubmitResponse) => void;
}

export default function AssessmentModal({ sessionId, kind, onClose, onSubmit }: Props) {
  const questions = kind === "phq9" ? PHQ9_QUESTIONS_TR : GAD7_QUESTIONS_TR;
  const [answers, setAnswers] = useState<(number | null)[]>(
    Array(questions.length).fill(null)
  );
  const [currentQ, setCurrentQ] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<AssessmentSubmitResponse | null>(null);
  const [error, setError] = useState<string>("");

  const handleAnswer = (value: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQ] = value;
    setAnswers(newAnswers);
    if (currentQ < questions.length - 1) {
        setCurrentQ(currentQ + 1);
      }


  };

  const handleSubmit = async () => {
    if(answers.includes(null)){
        setError("Lütfen tüm soruları cevaplayın.");
        return;

    }
    setSubmitting(true)
    setError("");
    try{
        const response = await submitAssessment({
            session_id: sessionId || undefined,
            kind:kind,
            answers: answers as number[],
        });
        setResult(response);
        markAssessmentTaken();
        onSubmit?.(response);

    } catch (err: any) {
        setError(err.message || "Test sonuçları gönderilirken bir hata oluştu.");
      } finally {
        setSubmitting(false);
      }
    };



    


  // RESULT VIEW — submit sonrası
  if (result) {
    const a = result.assessment;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
        <div className="w-full max-w-md rounded-2xl bg-white dark:bg-cbt-dark-surface p-6 shadow-xl">
          <div className="flex justify-between items-start mb-4">
            <h2 className="text-lg font-medium text-cbt-text dark:text-cbt-dark-text">
              Sonuç
            </h2>
            <button onClick={onClose} className="text-cbt-textMuted">
              <X size={20} />
            </button>
          </div>

          {/* Skor gösterimi */}
          <div className="mb-4">
            <div className="text-3xl font-light text-cbt-text dark:text-cbt-dark-text">
              {a.total_score} / {kind === "phq9" ? 27 : 21}
            </div>
            <div className="mt-2 flex items-center gap-2">
              <span className={`inline-block w-3 h-3 rounded-full ${SEVERITY_COLORS[a.severity]}`} />
              <span className="text-sm text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                {SEVERITY_LABELS_TR[a.severity]}
              </span>
            </div>
          </div>

          {/* Crisis alert */}
          {result.crisis_alert && (
            <div className="mb-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <div className="flex gap-3">
                <AlertTriangle className="shrink-0 text-red-600 dark:text-red-400" size={20} />
                <p className="text-sm text-red-900 dark:text-red-200 leading-relaxed">
                  {result.crisis_message}
                </p>
              </div>
            </div>
          )}

          <p className="text-xs text-cbt-textMuted mb-4 leading-relaxed">
            Bu bir klinik tanı değildir — bir tarama ölçeğidir. Skorun {a.severity === "moderate" || a.severity === "moderately_severe" || a.severity === "severe" ? "orta ve üzeri" : "hafif"} kategorisinde. Bu bilgi zaman içindeki değişimini görmek için işaretlenir.
          </p>

          <button
            onClick={onClose}
            className="w-full py-3 rounded-xl bg-cbt-accent text-white font-medium"
          >
            Tamam
          </button>
        </div>
      </div>
    );
  }


  // QUESTION VIEW
  const q = questions[currentQ];
  const answered = answers.filter((a) => a !== null).length;
  const progress = (answered / questions.length) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-cbt-dark-surface p-6 shadow-xl">
        {/* Header + progress */}
        <div className="flex justify-between items-center mb-1">
          <div className="text-xs text-cbt-textMuted">
            {kind === "phq9" ? "PHQ-9" : "GAD-7"} · Soru {currentQ + 1}/{questions.length}
          </div>
          <button onClick={onClose} className="text-cbt-textMuted">
            <X size={18} />
          </button>
        </div>
        {currentQ > 0 && (
  <button
    onClick={() => setCurrentQ(currentQ - 1)}
    className="text-xs text-cbt-textMuted mb-3"
  >
    ← Önceki soru
  </button>
)}
        <div className="h-1 bg-cbt-border rounded-full mb-6 overflow-hidden">
          <div
            className="h-full bg-cbt-accent transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Intro (sadece ilk soruda) */}
        {currentQ === 0 && (
          <p className="text-xs text-cbt-textMuted mb-4 leading-relaxed">
            Son 2 hafta boyunca, aşağıdaki sorunlar sizi ne sıklıkta rahatsız etti?
          </p>
        )}

        {/* Question */}
        <h3 className="text-base text-cbt-text dark:text-cbt-dark-text mb-6 leading-relaxed">
          {q}
        </h3>

        {/* Options */}
        <div className="space-y-2 mb-4">
          {LIKERT_OPTIONS_TR.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleAnswer(opt.value)}
              className={`w-full py-3 px-4 rounded-xl border transition-all text-left ${
                answers[currentQ] === opt.value
                  ? "border-cbt-accent bg-cbt-accent/10 text-cbt-accent"
                  : "border-cbt-border hover:border-cbt-borderStrong text-cbt-text dark:text-cbt-dark-text"
              }`}
            >
              <span className="text-xs text-cbt-textMuted mr-3">{opt.value}</span>
              {opt.label}
            </button>
          ))}
        </div>

        {/* Submit button — son soruda */}
        {currentQ === questions.length - 1 && answers[currentQ] !== null && (
          <button
            onClick={handleSubmit}
            disabled={submitting || answers.includes(null)}
            className="w-full py-3 rounded-xl bg-cbt-accent text-white font-medium disabled:opacity-50"
          >
            {submitting ? "Kaydediliyor..." : "Sonucu Gör"}
          </button>
        )}

        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
      </div>
    </div>
  );
}