// Cevapta kullanılan kartı egzersiz aracına eşler.
//
// Neva bir teknikten bahsettiğinde kullanıcı onu okuyup kapatıyordu;
// aracın kendisi başka sayfada duruyor. Eşleme kart kimliği üzerinden:
// modelin ne dediğini tahmin etmiyoruz, hangi kartın kullanıldığına
// bakıyoruz. Kart listesi cards/cbt_cards.jsonl ile elle eşleşiyor.

export interface ExerciseLink {
  href: string;
  label: string;
  note: string;
}

const BREATHING: ExerciseLink = {
  href: "/egzersizler/nefes",
  label: "Nefes egzersizini aç",
  note: "Görsel rehberle, bir dakikadan başlayarak",
};

const THOUGHT_RECORD: ExerciseLink = {
  href: "/egzersizler/dusunce-kaydi",
  label: "Düşünce kaydını aç",
  note: "Yedi soru, adım adım",
};

const SMALL_STEP: ExerciseLink = {
  href: "/egzersizler/kucuk-adim",
  label: "Küçük adım planını aç",
  note: "Eğer-o zaman, tek satır",
};

const CARD_TO_TOOL: Record<string, ExerciseLink> = {
  // Nefes / gevşeme
  pa_hyperv_005: BREATHING,
  pa_grounding_004: BREATHING,
  trauma_grounding_005: BREATHING,
  insom_relaxation_008: BREATHING,
  ang_timeout_005: BREATHING,

  // Düşünce kaydı
  ha_thoughtrec_008: THOUGHT_RECORD,
  pa_thoughtrec_009: THOUGHT_RECORD,
  dep_thoughtrec_007: THOUGHT_RECORD,
  lse_thoughtrec_004: THOUGHT_RECORD,
  lse_innercritic_005: THOUGHT_RECORD,
  insom_thoughtrec_007: THOUGHT_RECORD,
  work_thoughtrec_007: THOUGHT_RECORD,
  soc_thoughtrec_007: THOUGHT_RECORD,
  soc_postevent_006: THOUGHT_RECORD,
  grief_thought_008: THOUGHT_RECORD,
  proc_thoughts_006: THOUGHT_RECORD,
  ang_thoughts_006: THOUGHT_RECORD,
  exam_thoughts_004: THOUGHT_RECORD,
  ga_4c_008: THOUGHT_RECORD,
  trans_cognitive_009: THOUGHT_RECORD,
  body_assumptions_006: THOUGHT_RECORD,
  pain_catastrophizing_005: THOUGHT_RECORD,
  fin_future_009: THOUGHT_RECORD,

  // Küçük adım / eğer-o zaman
  proc_ifthen_005: SMALL_STEP,
  dep_actsched_004: SMALL_STEP,
  lse_smallwins_007: SMALL_STEP,
  soc_experiment_008: SMALL_STEP,
  pain_pacing_004: SMALL_STEP,
  fin_smallcontrol_008: SMALL_STEP,
};

/**
 * Bu turda önerilebilecek tek araç. Güvenlik kapısı egzersizi
 * kapattıysa (kriz, destekleyici-egzersizsiz yol) hiçbir şey dönmez —
 * o anda gereken bir form değil.
 */
export function exerciseLinkFor(
  cardIds: string[] | undefined,
  opts: { allowCbt: boolean; blocksExercise?: boolean }
): ExerciseLink | null {
  if (!cardIds || !opts.allowCbt || opts.blocksExercise) return null;
  for (const id of cardIds) {
    const tool = CARD_TO_TOOL[id];
    if (tool) return tool;
  }
  return null;
}
