import ExerciseShell from "@/components/exercises/ExerciseShell";
import ThoughtRecord from "@/components/exercises/ThoughtRecord";

export const metadata = {
  title: "Düşünce kaydı — Neva",
  description: "Yedi soruluk bilişsel davranışçı terapi düşünce kaydı.",
};

export default function DusunceKaydiPage() {
  return (
    <ExerciseShell
      title="Düşünce kaydı"
      intro="Bilişsel davranışçı terapinin temel aracı. Bir düşünceyi yazıya dökmek onu yok etmez; ama kafanın içinden çıkarıp masaya koyar. Yedi soru, beş dakika."
      sources={[
        { id: "lse_thoughtrec_004", title: "Öz-eleştiri düşünce kaydı: yedi soruluk pratik", topic: "low_self_esteem" },
        { id: "ga_4c_008", title: "4C: Yakala, Sınıflandır, Sorgula, Değiştir", topic: "gad" },
        { id: "soc_thoughtrec_007", title: "Sosyal tahminleri sınamak", topic: "social_anxiety" },
        { id: "lse_innercritic_005", title: "İç eleştirmenin tuzakları: yedi düşünce kalıbı", topic: "low_self_esteem" },
      ]}
    >
      <ThoughtRecord />
    </ExerciseShell>
  );
}
