import ExerciseShell from "@/components/exercises/ExerciseShell";
import SmallStep from "@/components/exercises/SmallStep";

export const metadata = {
  title: "Küçük adım — Neva",
  description: "Eğer-o zaman planı: tek satırlık, bugün yapılabilir bir adım.",
};

export default function KucukAdimPage() {
  return (
    <ExerciseShell
      title="Küçük adım"
      intro="Motivasyon beklenmez, üretilir; hareket önce gelir. Bir tetikleyiciye tek bir davranış bağla. Büyük hedef değil — bugün yapılınca “yaptım” diyebileceğin kadar küçük."
      sources={[
        { id: "proc_ifthen_005", title: "Eğer-o zaman planı", topic: "procrastination" },
        { id: "dep_actsched_004", title: "Davranışsal aktivasyon — küçük başla", topic: "depression" },
        { id: "lse_smallwins_007", title: "Küçük adım, SMART hedef", topic: "low_self_esteem" },
      ]}
    >
      <SmallStep />
    </ExerciseShell>
  );
}
