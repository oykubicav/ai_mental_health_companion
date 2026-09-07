import ExerciseShell from "@/components/exercises/ExerciseShell";
import Breathing from "@/components/exercises/Breathing";

export const metadata = {
  title: "Nefes — Neva",
  description: "Diyafram, kutu ve 4-7-8 nefesi için sessiz bir görsel rehber.",
};

export default function NefesPage() {
  return (
    <ExerciseShell
      title="Nefes"
      intro="Ses yok, sayaç yok. Daire büyüyünce al, küçülünce ver. Bir dakika bile bedenin alarm düzeyini düşürür; sakinleşmek zorunda değilsin, sadece nefes al."
      sources={[
        { id: "pa_hyperv_005", title: "Diyafragmatik nefes ve hiperventilasyon", topic: "panic" },
        { id: "insom_relaxation_008", title: "Rahatlama — beden uyarılmışsa uyku gelmez", topic: "insomnia" },
        { id: "ga_worrydiary_004", title: "Endişe günlüğü", topic: "gad" },
      ]}
    >
      <Breathing />
    </ExerciseShell>
  );
}
