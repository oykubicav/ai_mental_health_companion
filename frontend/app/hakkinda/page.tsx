import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import PageShell, { Block } from "@/components/PageShell";

export const metadata = {
  title: "Neva nedir",
  description:
    "Neva, bilişsel davranışçı terapi temelli yöntemleri Türkçe konuşan bir destek asistanıdır.",
};

export default function HakkindaPage() {
  return (
    <PageShell
      title="Neva nedir?"
      intro="Zorlandığın bir günde, yargılanmadan konuşabileceğin ve bilimsel temeli olan yöntemlerle birlikte düşünebileceğin bir alan."
    >
      <Block heading="Neden var">
        <p>
          Bir psikoloğa ulaşmak her zaman kolay değil. Randevu haftalar sonrasına
          düşebiliyor, maliyetli olabiliyor, bazen de insan ilk adımı atmaya
          hazır hissetmiyor. Bu aradaki boşlukta çoğu kişi ya hiçbir şey yapmıyor
          ya da internette dağınık, kaynağı belirsiz tavsiyelerin arasında
          kayboluyor.
        </p>
        <p>
          Neva bu boşluk için tasarlandı. Terapinin yerini almak için değil;
          o adımı atana kadar geçen sürede işine yarayacak, kaynağı belli
          yöntemleri Türkçe ve anlaşılır biçimde ulaşılabilir kılmak için.
        </p>
      </Block>

      <Block id="nasil" heading="Nasıl çalışır">
        <p>
          Neva serbest çağrışımla konuşan bir sohbet botu değil. Yazdığın her
          mesaj için önce konu belirleniyor, ardından o konuya ait klinik
          rehberlerden derlenmiş içerikler getiriliyor ve cevap bu içeriklere
          dayandırılarak yazılıyor.
        </p>
        <p>
          Cevap sana ulaşmadan önce ayrı bir kontrol katmanından geçiyor: tanı
          koyan, ilaç öneren, boş vaatte bulunan ya da uzman yönlendirmesini
          geciktiren ifadeler varsa cevap yeniden yazdırılıyor.
        </p>
        <p>
          Her cevabın altındaki <span className="font-medium">nasıl üretildi</span>{" "}
          bağlantısına tıklayarak hangi konuda arama yapıldığını, kaç içerik
          parçasının kullanıldığını ve kalite kontrolünden geçip geçmediğini
          görebilirsin.
        </p>
      </Block>

      <Block id="sinirlar" heading="Neyi yapmaz">
        <p>
          Neva tanı koymaz. &quot;Sende depresyon var&quot; ya da &quot;bu bir
          anksiyete bozukluğu&quot; gibi bir cümle kurmaz; kuramaz. Tanı, kişiyi
          bütünüyle değerlendiren bir uzmanın işidir.
        </p>
        <p>
          İlaç önermez, mevcut tedaviyle ilgili yorum yapmaz, uzmana gitmeyi
          erteletmez. Aksine, tabloyu ciddi gördüğü noktalarda seni uzmana
          yönlendirir.
        </p>
        <p>
          Kriz anları için tasarlanmadı. Kendine zarar verme düşüncesi, tıbbi
          aciliyet ya da güvenlik riski içeren durumlarda Neva sohbeti sürdürmek
          yerine acil yardım kaynaklarına yönlendirir.
        </p>
      </Block>

      <Block heading="Ne ne için">
        <p>
          Neva üç parçadan oluşuyor ve hangisine ne zaman gideceğini bilmek
          işini kolaylaştırır.
        </p>
        <ul className="not-prose grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <NavCard
            href="/"
            title="Sohbet"
            body="Anlatmak istediğin bir şey olduğunda. Konuşma, sonu belli; yirmi dakika civarı."
          />
          <NavCard
            href="/egzersizler"
            title="Egzersizler"
            body="Konuşmadan da kullanılır: nefes, düşünce kaydı, küçük adım planı."
          />
          <NavCard
            href="/gunluk"
            title="Günlük"
            body="Her gün kısaca ne olduğunu yazdığın yer. Yapay zekâ okumaz."
          />
        </ul>
      </Block>

      <Block heading="Kimin için">
        <p>
          Gündelik hayatını sürdürebilen ama kaygı, düşük ruh hali, uyku sorunu,
          iş yükü ya da bir yaşam değişimiyle boğuşan yetişkinler için uygun.
        </p>
        <p>
          Ağır ve süregelen bir tablo yaşıyorsan, aktif bir tedavi sürecindeysen
          ya da kriz yaşıyorsan Neva doğru araç değil — bu durumlarda doğrudan
          bir uzmanla çalışmak gerekiyor.
        </p>
      </Block>
    </PageShell>
  );
}

function NavCard({ href, title, body }: { href: string; title: string; body: string }) {
  return (
    <li>
      <Link
        href={href}
        className="group h-full flex flex-col p-5 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong hover:-translate-y-0.5 transition-all"
      >
        <span className="flex items-center justify-between gap-2 mb-1.5">
          <span className="display text-[20px] text-cbt-text dark:text-cbt-dark-text">{title}</span>
          <ArrowUpRight
            size={15}
            strokeWidth={2}
            className="shrink-0 text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover:text-cbt-accent dark:group-hover:text-cbt-dark-accent transition-colors"
          />
        </span>
        <span className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
          {body}
        </span>
      </Link>
    </li>
  );
}
