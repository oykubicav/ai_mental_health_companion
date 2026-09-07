"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Search, X, ChevronRight } from "lucide-react";
import { getTopics, listCards, getCard } from "@/lib/api";
import type { CBTCardSummary, CBTCardOut, TopicInfo } from "@/lib/types";
import ThemeToggle from "./ThemeToggle";

const TYPE_LABELS: Record<string, string> = {
  psychoeducation: "Bilgilendirme",
  self_assessment: "Kendini değerlendirme",
  exercise: "Egzersiz",
  technique: "Teknik",
  in_attack: "Anlık destek",
  safety: "Güvenlik",
};

const TOPIC_DESCRIPTIONS: Record<string, string> = {
  health_anxiety:
    "Bedensel belirtilere dair sürekli endişe, hastalık korkusu ve güvence arayışı üzerine.",
  panic: "Panik atakları anlamak, atak anında ve sonrasında ne yapılabileceği üzerine.",
  gad: "Sürekli endişe, kontrol edilemeyen düşünceler ve gerginlikle çalışmak üzerine.",
  depression:
    "Düşük ruh hali, isteksizlik ve olumsuz düşünce döngüleriyle başa çıkma üzerine.",
  low_self_esteem:
    "Kendine dair olumsuz inançlar ve iç eleştirmenle çalışmak üzerine.",
  insomnia: "Uykuya dalamama, gece uyanmaları ve uyku düzenini onarmak üzerine.",
  work_stress:
    "İş yükü, tükenmişlik ve iş-yaşam sınırlarını korumak üzerine.",
  relationship_stress:
    "İlişki çatışmaları, iletişim sorunları ve bağ kurma üzerine.",
  grief_loss: "Kayıp, yas süreci ve kayıpla yaşamayı öğrenmek üzerine.",
  life_transitions:
    "Taşınma, ayrılık, mezuniyet gibi büyük yaşam değişimlerine uyum üzerine.",
  trauma_awareness:
    "Zor yaşantıların etkilerini tanımak ve destek seçeneklerini bilmek üzerine.",
  social_anxiety:
    "Başkalarının değerlendirmesinden çekinme, sosyal ortamlarda gerginlik ve kaçınma üzerine.",
  procrastination:
    "Başlayamama, sürekli sonraya bırakma ve bunun getirdiği suçluluk döngüsü üzerine.",
  anger:
    "Çabuk parlama, öfkeyi ifade etme biçimleri ve sonrasındaki onarım üzerine.",
  exam_anxiety:
    "Sınav öncesi gerginlik, sınavda donma ve sonuç beklerken yaşananlar üzerine.",
  body_image:
    "Bedeninle kurduğun ilişki, karşılaştırma alışkanlığı ve görünüm üzerinden kendini değerlendirme üzerine.",
  chronic_pain:
    "Uzun süren ağrı ya da hastalıkla yaşamak: hareket, tempo, alevlenme günleri ve çevreyle ilişki üzerine.",
  financial_stress:
    "Para kaygısının uykuya, karar vermeye, ilişkilere ve kendine bakışına yansıması üzerine.",
};

export default function CardList() {
  const [topics, setTopics] = useState<TopicInfo[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<string>("");
  const [q, setQ] = useState("");
  const [cards, setCards] = useState<CBTCardSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openCard, setOpenCard] = useState<CBTCardOut | null>(null);
  const [openLoading, setOpenLoading] = useState(false);

  // /cards?topic=insomnia gibi bağlantılar modülü doğrudan açar.
  useEffect(() => {
    const fromUrl = new URLSearchParams(window.location.search).get("topic");
    if (fromUrl) setSelectedTopic(fromUrl);
  }, []);

  useEffect(() => {
    getTopics()
      .then((r) => setTopics(r.topics))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selectedTopic && !q) return;
    setLoading(true);
    setError(null);
    const t = setTimeout(() => {
      listCards({
        topic: selectedTopic || undefined,
        q: q || undefined,
        limit: 50,
      })
        .then((r) => {
          setCards(r.cards);
          setTotal(r.total);
        })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, q ? 200 : 0);
    return () => clearTimeout(t);
  }, [selectedTopic, q]);

  async function openDetail(id: string) {
    setOpenLoading(true);
    try {
      const c = await getCard(id);
      setOpenCard(c);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setOpenLoading(false);
    }
  }

  const selectedTopicInfo = topics.find((t) => t.topic === selectedTopic);
  const showingList = Boolean(selectedTopic || q);

  return (
    <div className="min-h-screen bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-30 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            {showingList ? (
              <button
                onClick={() => {
                  setSelectedTopic("");
                  setQ("");
                }}
                className="flex items-center gap-1 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
              >
                <ArrowLeft size={15} strokeWidth={2} />
                Konular
              </button>
            ) : (
              <a
                href="/"
                className="flex items-center gap-1 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
              >
                <ArrowLeft size={15} strokeWidth={2} />
                Ana sayfa
              </a>
            )}
          </div>
          <span className="display text-[18px] text-cbt-text dark:text-cbt-dark-text truncate max-w-[45%]">
            {showingList && selectedTopicInfo
              ? selectedTopicInfo.display_name_tr
              : "Neva"}
          </span>
          <div className="flex items-center gap-2">
            <a
              href="/egzersizler"
              className="hidden sm:flex px-3 h-9 items-center rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Egzersizler
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {!showingList && (
        <div className="relative grain">
          <div className="hero-orb hero-orb-1 animate-drift !w-[300px] !h-[300px] !top-[-20%] !left-[60%]" />
          <div className="relative max-w-4xl mx-auto px-6 pt-16 pb-10">
            <h1 className="display animate-hero-in text-[42px] sm:text-[52px] leading-[1.05] text-cbt-text dark:text-cbt-dark-text mb-5">
              Neva ne biliyor
            </h1>
            <p
              className="animate-hero-in text-[17px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed max-w-2xl"
              style={{ animationDelay: "80ms" }}
            >
              Cevapların dayandığı bütün içerik burada, olduğu gibi. On sekiz
              konu, her birinde on kart; hepsi bir klinik psikolog tarafından
              okundu. Sohbete girmeden de okuyabilirsin.
            </p>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Search */}
        <div className="relative mb-8">
          <Search
            size={16}
            strokeWidth={2}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-cbt-textMuted dark:text-cbt-dark-textMuted"
          />
          <input
            className="w-full pl-11 pr-10 h-12 bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border rounded-2xl text-[15px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted dark:placeholder:text-cbt-dark-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
            placeholder="Ara — örn. uyku, panik, iç eleştirmen"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {q && (
            <button
              onClick={() => setQ("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text"
              aria-label="Temizle"
            >
              <X size={15} strokeWidth={2.2} />
            </button>
          )}
        </div>

        {error && (
          <div className="text-[13px] text-cbt-danger dark:text-cbt-dark-danger bg-cbt-dangerSoft dark:bg-cbt-dark-dangerSoft border border-cbt-danger/20 dark:border-cbt-dark-danger/30 rounded-xl px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {/* Topic overview */}
        {!showingList && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {topics.map((t, i) => (
              <button
                key={t.topic}
                onClick={() => setSelectedTopic(t.topic)}
                className="text-left p-6 rounded-[20px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong transition-all active:scale-[0.99] group animate-slide-up"
                style={{
                  animationDelay: `${Math.min(i * 40, 400)}ms`,
                  animationFillMode: "backwards",
                }}
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="display text-[21px] leading-tight text-cbt-text dark:text-cbt-dark-text">
                    {t.display_name_tr}
                  </span>
                  <ChevronRight
                    size={16}
                    strokeWidth={2}
                    className="shrink-0 text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover:translate-x-0.5 transition-transform"
                  />
                </div>
                <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
                  {TOPIC_DESCRIPTIONS[t.topic] || ""}
                </p>
              </button>
            ))}
          </div>
        )}

        {/* Content list within a topic / search results */}
        {showingList && (
          <>
            {selectedTopicInfo && !q && (
              <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-6 max-w-2xl">
                {TOPIC_DESCRIPTIONS[selectedTopic] || ""}
              </p>
            )}

            <div className="space-y-2.5">
              {loading && cards.length === 0
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-16 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/40 dark:border-cbt-dark-border/40 shimmer"
                    />
                  ))
                : cards.map((c, i) => (
                    <button
                      key={c.id}
                      onClick={() => openDetail(c.id)}
                      className="w-full text-left px-5 py-4 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong transition-all active:scale-[0.995] group animate-slide-up flex items-center justify-between gap-4"
                      style={{
                        animationDelay: `${Math.min(i * 30, 300)}ms`,
                        animationFillMode: "backwards",
                      }}
                    >
                      <div>
                        <div className="display text-[17px] leading-snug text-cbt-text dark:text-cbt-dark-text">
                          {c.title_tr}
                        </div>
                        <div className="mt-1 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
                          {TYPE_LABELS[c.type] || c.type}
                        </div>
                      </div>
                      <ChevronRight
                        size={16}
                        strokeWidth={2}
                        className="shrink-0 text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover:translate-x-0.5 transition-transform"
                      />
                    </button>
                  ))}
            </div>

            {cards.length === 0 && !loading && (
              <div className="text-[14px] text-cbt-textMuted dark:text-cbt-dark-textMuted text-center py-16">
                Sonuç bulunamadı.
              </div>
            )}
          </>
        )}
      </div>

      {openCard && (
        <div
          className="fixed inset-0 z-40 bg-black/40 dark:bg-black/60 backdrop-blur-sm p-4 flex items-center justify-center animate-fade-in"
          onClick={() => setOpenCard(null)}
        >
          <div
            className="max-w-2xl w-full bg-cbt-surface dark:bg-cbt-dark-surface rounded-3xl shadow-modal max-h-[85vh] overflow-hidden flex flex-col animate-modal-in border border-cbt-border/40 dark:border-cbt-dark-border/40"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-cbt-border/50 dark:border-cbt-dark-border/50 px-7 py-5 flex items-start justify-between gap-3">
              <div>
                <h2 className="display text-[24px] leading-tight text-cbt-text dark:text-cbt-dark-text">
                  {openCard.title_tr}
                </h2>
                <div className="mt-1 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
                  {TYPE_LABELS[openCard.type] || openCard.type}
                </div>
              </div>
              <button
                className="flex items-center justify-center w-9 h-9 rounded-full text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text hover:bg-cbt-surfaceMuted dark:hover:bg-cbt-dark-surfaceMuted transition-colors"
                onClick={() => setOpenCard(null)}
                aria-label="Kapat"
              >
                <X size={16} strokeWidth={2} />
              </button>
            </div>
            <div className="px-7 py-6 overflow-y-auto chat-scroll text-[15px] leading-relaxed text-cbt-text dark:text-cbt-dark-text whitespace-pre-wrap">
              {openCard.content_tr}
              {openCard.safety_notes && (
                <div className="mt-6 text-[13px] text-cbt-warning dark:text-cbt-dark-warning bg-cbt-warningSoft dark:bg-cbt-dark-warningSoft border border-cbt-warning/20 dark:border-cbt-dark-warning/30 rounded-xl px-4 py-3">
                  <div className="font-semibold mb-1">Önemli</div>
                  {openCard.safety_notes}
                </div>
              )}

              <div className="mt-8 pt-4 border-t border-cbt-border/50 dark:border-cbt-dark-border/50 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted whitespace-normal">
                {openCard.review_status === "clinician_reviewed" && (
                  <span className="text-cbt-success dark:text-cbt-dark-success">
                    Klinik psikolog onaylı
                  </span>
                )}
                <span className="font-mono">{openCard.id}</span>
                {openCard.source_refs?.length > 0 && (
                  <a href="/kaynaklar" className="underline underline-offset-4 hover:text-cbt-text dark:hover:text-cbt-dark-text">
                    {openCard.source_refs.length} kaynak
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {openLoading && (
        <div className="fixed bottom-5 right-5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted bg-cbt-surface dark:bg-cbt-dark-surface shadow-soft border border-cbt-border dark:border-cbt-dark-border rounded-xl px-4 py-2.5">
          Yükleniyor…
        </div>
      )}
    </div>
  );
}
