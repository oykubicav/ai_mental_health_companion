"use client";
import { useEffect, useState } from "react";
import { X, Loader2, Info } from "lucide-react";
import { getTransparency } from "@/lib/api";
import type { TransparencyView } from "@/lib/types";

interface Props {
    turnId: string;
    onClose: () => void;
  }

  const BOUNDARY_LABELS: Record<string, string> = {
    normal: "Normal seans",
    warmup: "Isınma — cevaplar kısaltılıyor",
    closing: "Kapanış teklifi",
    extended: "Uzatılmış",
    hard_close: "Sert kapanış",
  };

  const MODULE_LABELS: Record<string, string> = {
    health_anxiety: "Sağlık kaygısı",
    panic: "Panik",
    gad: "Yaygın kaygı",
    depression: "Düşük ruh hali",
    low_self_esteem: "Özdeğer",
    insomnia: "Uyku",
    work_stress: "İş stresi",
    relationship_stress: "İlişkiler",
    grief_loss: "Kayıp ve yas",
    life_transitions: "Yaşam değişimleri",
    social_anxiety: "Sosyal kaygı",
    procrastination: "Erteleme",
    anger: "Öfke",
    exam_anxiety: "Sınav kaygısı",
    body_image: "Beden imajı",
    chronic_pain: "Kronik ağrı",
    financial_stress: "Maddi kaygı",
    trauma_awareness: "Zor yaşantılar",
    safety: "Güvenlik",
    boundary: "Kapsam dışı",
    unknown: "Henüz belirsiz",
  };

  // Konuşma durumu — cevabın "nasıl" yazıldığını belirleyen eksen.
  const STATE_LABELS: Record<string, string> = {
    vague: "Henüz belirsiz anlatım",
    withdrawn: "Kısa cevaplar",
    self_critical: "Kendine sert konuşma",
    ambivalent: "Kararsızlık",
    directive_request: "Doğrudan yön isteği",
    own_evidence: "Kendi deneyiminden kanıt",
    technique_failed: "Denenen şey işe yaramadı",
    misunderstood: "Yanlış anlaşılma",
    formulating: "Toparlama anı",
    winding_down: "Kapanışa yaklaşma",
    neutral: "Belirgin bir örüntü yok",
  };

  const RISK_LABELS: Record<string, string> = {
    none: "Yok",
    low: "Düşük",
    medium: "Orta",
    high: "Yüksek",
    critical: "Kritik",
  };

export default function TransparencyPanel({ turnId, onClose }: Props) {
    const [data, setData] = useState<TransparencyView | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string>("");
    useEffect(() => {
        let cancelled = false;
        async function load() {
          setLoading(true);
          setError("");
          setData(null);
          try {
            const transview = await getTransparency(turnId);
            if (!cancelled) setData(transview);
          } catch (err: unknown) {
            if (!cancelled) {
              setError(err instanceof Error ? err.message : "Sonuçlar yüklenirken bir hata oluştu.");
            }
          } finally {
            if (!cancelled) setLoading(false);
          }
        }
        void load();
        return () => {
          cancelled = true;
        };
      }, [turnId]);

      return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl bg-white dark:bg-cbt-dark-surface p-6 shadow-xl">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Info className="text-cbt-accent" size={18} />
                <h2 className="text-base font-medium text-cbt-text dark:text-cbt-dark-text">
                  Bu cevap nasıl üretildi?
                </h2>
              </div>
              <button onClick={onClose} className="text-cbt-textMuted">
                <X size={18} />
              </button>
            </div>
    
            {loading && (
              <div className="py-8 flex justify-center">
                <Loader2 className="animate-spin text-cbt-textMuted" size={20} />
              </div>
            )}
    
            {error && (
              <p className="py-4 text-sm text-red-600">{error}</p>
            )}
    
            {data && (
              <div className="space-y-4 text-sm">
                {/* Model */}
                <Section title="Model">
                  <p className="text-cbt-textSecondary">{data.model_version || "—"}</p>
                </Section>
    
                {/* Intent */}
                {data.intent && (
                  <Section title="Hangi konuda içerik arandı">
                    <p className="text-cbt-textSecondary">
                      {MODULE_LABELS[data.intent.module] || data.intent.module}
                      <span className="text-cbt-textMuted">
                        {" "}· eşleşme %{Math.round(data.intent.confidence * 100)}
                      </span>
                    </p>
                    <p className="text-xs text-cbt-textMuted mt-1 leading-relaxed">
                      Bu bir tanı ya da değerlendirme değil — yalnızca hangi konu
                      başlığındaki materyallerin getirileceğini belirleyen bir
                      arama etiketi.
                    </p>
                  </Section>
                )}

                {/* Konuşma yaklaşımı */}
                {data.intent?.conversation_state &&
                  data.intent.conversation_state !== "neutral" && (
                    <Section title="Konuşma nasıl yürütüldü">
                      <p className="text-cbt-textSecondary">
                        {STATE_LABELS[data.intent.conversation_state] ||
                          data.intent.conversation_state}
                      </p>
                      <p className="text-xs text-cbt-textMuted mt-1 leading-relaxed">
                        Cevabın içeriği kadar biçimi de seçiliyor: bu turda
                        {" "}
                        {data.intent.process_card_ids?.length || 0} yaklaşım kartı
                        kullanıldı. Bu kartlar Neva&apos;nın ne söyleyeceğini değil,
                        nasıl söyleyeceğini belirliyor — henüz klinisyen
                        incelemesinden geçmediler.
                      </p>
                    </Section>
                  )}

                {/* Retrieved cards */}
                {data.retrieved_card_ids && data.retrieved_card_ids.length > 0 && (
                  <Section title={`Kullanılan materyal (${data.retrieved_card_ids.length})`}>
                    <p className="text-cbt-textSecondary text-xs leading-relaxed">
                      Cevap, klinik rehberlerden derlenmiş {data.retrieved_card_ids.length} içerik
                      parçası temel alınarak yazıldı.
                    </p>
                  </Section>
                )}

                {/* Safety route */}
                {data.safety && (
                  <Section title="Güvenlik kontrolü">
                    <p className="text-cbt-textSecondary">
                      Risk düzeyi: {RISK_LABELS[data.safety.highest_risk] || data.safety.highest_risk}
                      {!data.safety.allow_cbt && " · Yönlendirme yapıldı"}
                    </p>
                  </Section>
                )}
    
                {/* Boundary state */}
                {data.boundary_state && (
                  <Section title="Seans durumu">
                    <p className="text-cbt-textSecondary">
                      {BOUNDARY_LABELS[data.boundary_state] || data.boundary_state}
                    </p>
                  </Section>
                )}
    
                {/* Critic */}
                {data.critic && (
                  <Section title="Kalite kontrolü">
                    <p className="text-cbt-textSecondary">
                      {data.critic.passed ? "✓ Geçti" : "✗ Kalıp ihlali"}
                      {data.critic.rewrites > 0 && ` · ${data.critic.rewrites} kez yeniden yazıldı`}
                    </p>
                  </Section>
                )}
    
                {/* KVKK notu */}
                <p className="text-xs text-cbt-textMuted leading-relaxed pt-3 border-t border-cbt-border">
                  Bu bilgi cevabımın nasıl üretildiğinin şeffaflığı için gösteriliyor —
                  KVKK ve EU AI Act "kararın açıklanabilir olması" ilkesine uygun.
                  Senin mesajının içeriği burada gösterilmez (kısa süreli tutulur, silinir).
                </p>
              </div>
            )}
          </div>
        </div>
      );
    }
    
    
    function Section({ title, children }: { title: string; children: React.ReactNode }) {
      return (
        <div>
          <div className="text-xs font-medium text-cbt-textMuted mb-1 uppercase tracking-wide">
            {title}
          </div>
          {children}
        </div>
      );
    }







