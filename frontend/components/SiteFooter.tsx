import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="border-t border-cbt-border/50 dark:border-cbt-dark-border/50">
      <div className="max-w-5xl mx-auto px-6 py-14">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="text-[17px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-3">
              Neva
            </div>
            <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed max-w-xs">
              Bilişsel davranışçı terapi temelli, Türkçe bir destek asistanı.
            </p>
          </div>

          <FooterColumn title="Neva">
            <FooterLink href="/hakkinda">Neva nedir</FooterLink>
            <FooterLink href="/hakkinda#nasil">Nasıl çalışır</FooterLink>
            <FooterLink href="/cards">Konular</FooterLink>
            <FooterLink href="/egzersizler">Egzersizler</FooterLink>
            <FooterLink href="/gunluk">Günlük</FooterLink>
          </FooterColumn>

          <FooterColumn title="Güven">
            <FooterLink href="/kaynaklar">Bilimsel kaynaklar</FooterLink>
            <FooterLink href="/gizlilik">Gizlilik ve veriler</FooterLink>
            <FooterLink href="/hakkinda#sinirlar">Sınırlarımız</FooterLink>
          </FooterColumn>

          <FooterColumn title="Destek">
            <FooterLink href="/acil">Acil durumlar</FooterLink>
            <FooterLink href="/login">Giriş yap</FooterLink>
            <FooterLink href="/register">Hesap oluştur</FooterLink>
          </FooterColumn>
        </div>

        <div className="pt-8 border-t border-cbt-border/50 dark:border-cbt-dark-border/50">
          <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed">
            Neva bir terapist, hekim ya da acil servis değildir; tanı koymaz,
            tedavi önermez. Kendine zarar verme düşüncen varsa ya da acil bir
            durumdaysan{" "}
            <span className="font-semibold text-cbt-text dark:text-cbt-dark-text">
              112
            </span>
            'yi ara.
          </p>
          <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted mt-4">
            © {new Date().getFullYear()} Neva
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[13px] font-semibold text-cbt-text dark:text-cbt-dark-text mb-4">
        {title}
      </div>
      <ul className="space-y-2.5">{children}</ul>
    </div>
  );
}

function FooterLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <li>
      <Link
        href={href}
        className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
      >
        {children}
      </Link>
    </li>
  );
}
