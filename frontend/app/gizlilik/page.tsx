import PageShell, { Block } from "@/components/PageShell";

export const metadata = {
  title: "Gizlilik ve veriler",
  description:
    "Neva hangi verileri tutuyor, ne kadar süreyle saklıyor ve nasıl siliniyor.",
};

export default function GizlilikPage() {
  return (
    <PageShell
      title="Gizlilik ve veriler"
      intro="Ruh sağlığıyla ilgili konuştuğun bir yerde neyin saklandığını bilmek hakkın. Kısa ve açık anlatalım."
    >
      <Block heading="Üyelik zorunlu değil">
        <p>
          Neva&apos;yı hesap açmadan kullanabilirsin. Bu durumda kimliğinle
          ilişkilendirilebilecek hiçbir bilgi istenmiyor; oturumun tarayıcında
          tutulan geçici bir kimlikle yürüyor.
        </p>
        <p>
          Karşılığında sohbetlerin saklanmıyor — bir sonraki gelişinde
          sıfırdan başlıyorsun. Hangisinin sana uygun olduğuna sen karar
          ver; ikisi de tam olarak çalışıyor.
        </p>
      </Block>

      <Block heading="Mesajların ne kadar kalıyor">
        <p>
          Bu, hesabının olup olmamasına göre değişiyor ve ikisini ayrı ayrı
          anlatmak istiyoruz.
        </p>
        <p>
          <strong>Üyeliksiz kullanırsan</strong> mesajların yalnızca sohbetin
          sürdüğü kadar tutuluyor. Yaklaşık bir saat işlem yapılmazsa oturum ve
          içindeki bütün mesajlar otomatik olarak siliniyor. Geri getirilemez.
        </p>
        <p>
          <strong>Hesabın varsa</strong> sohbetlerin sen silene kadar
          saklanıyor. Bunu sen istediğin için yapıyoruz: eski konuşmalarına
          dönebilmen, kaldığın yerden devam edebilmen ve zaman içindeki
          değişimi görebilmen bunu gerektiriyor. Otomatik bir silme süresi
          yok — karar sende.
        </p>
        <p>
          Sistem kayıtlarına mesaj içeriği yazılmıyor. Kayıtlarda yalnızca
          teknik bilgiler bulunuyor: isteğin ne kadar sürdüğü, hangi konu
          başlığında arama yapıldığı, kalite kontrolünden geçip geçmediği.
        </p>
      </Block>

      <Block heading="Hesap açarsan">
        <p>
          E-posta adresin ve şifrenin şifrelenmiş özeti saklanıyor. Şifrenin
          kendisi hiçbir yerde açık biçimde tutulmuyor.
        </p>
        <p>
          Ölçüm yaptıysan sonuçların hesabınla ilişkilendiriliyor — zaman
          içindeki değişimi görebilmen için.
        </p>
        <p>
          Konuşmalarından bazı sinyaller çıkarılıyor: tekrar eden konular,
          denediğin teknikler ve bunların sana iyi gelip gelmediği. Bunlar
          Neva&apos;nın seni hatırlaması içindir, bir değerlendirme ya da tanı
          değildir ve yanılabilirler. Ne çıkarıldığını Gelişimim sayfasından
          görebilir, tek tuşla silebilirsin — sohbetlerin yerinde kalır.
        </p>
      </Block>

      <Block heading="Silme hakkı">
        <p>
          Sohbetlerini tek tek silebilirsin: sohbet listesindeki çöp kutusu
          simgesi o konuşmayı ve içindeki bütün mesajları kaldırır.
        </p>
        <p>
          Konuşmalardan çıkarılan notları ayrıca silebilirsin; bunun için
          sohbetlerinden vazgeçmen gerekmiyor.
        </p>
        <p>
          Hesabını silersen hesabına bağlı her şey — sohbetler, mesajlar,
          ölçüm sonuçları, çıkarılan notlar ve açık oturumlar — birlikte
          siliniyor. Bu işlem geri alınamıyor.
        </p>
      </Block>

      <Block heading="Oturum güvenliği">
        <p>
          Giriş yaptığında tarayıcına, JavaScript&apos;in okuyamadığı bir
          oturum çerezi bırakılıyor. Bu, sitede bir açık olsa bile oturumunun
          çalınmasını zorlaştırıyor.
        </p>
        <p>
          Hesabım sayfasından açık oturumlarını görebilir, tanımadığın bir
          cihazı kapatabilir ya da tek seferde hepsinden çıkabilirsin. Şifreni
          değiştirdiğinde diğer cihazlardaki oturumlar kendiliğinden kapanıyor.
        </p>
      </Block>

      <Block heading="Verilerin nereye gidiyor">
        <p>
          Bunu açıkça söylemek istiyoruz, çünkü çoğu uygulama söylemiyor:
          <strong> verilerin Türkiye dışında işleniyor.</strong>
        </p>
        <p>
          Veritabanı ve sunucu Avrupa Birliği sınırları içinde, Frankfurt&apos;ta.
          Yazdığın her mesaj, cevap üretilebilmesi için ABD merkezli
          Anthropic&apos;in altyapısına gönderiliyor. Gönderilmeden önce telefon
          numarası, e-posta, kimlik numarası gibi tanımlayıcılar metinden
          çıkarılıyor — ama mesajın içeriği olduğu gibi gidiyor. Neva
          mesajını okumadan cevap veremez; bu, ürünün doğası.
        </p>
        <p>
          Anthropic&apos;e API üzerinden gönderilen içerik model eğitiminde
          kullanılmıyor ve kalıcı olarak saklanmıyor. Hesap oluşturma ve şifre
          sıfırlama e-postaları da ABD merkezli bir servis (Resend) üzerinden
          gidiyor; orada yalnızca e-posta adresin işleniyor.
        </p>
        <p>
          Türkiye&apos;nin henüz hiçbir ülke için veri aktarımı yeterlilik kararı
          bulunmuyor. Bu yüzden Neva&apos;yı kullanmak, mesajlarının yurt dışında
          işlenmesini kabul etmek anlamına geliyor. Bu seni rahatsız ediyorsa
          en doğru karar Neva&apos;yı kullanmamak — bunu saklamak istemiyoruz.
        </p>
      </Block>

      <Block heading="İçerik kim tarafından incelendi">
        <p>
          Neva&apos;nın kullandığı bütün içerik — 18 konu başlığındaki 180 bilgi
          kartı ve 19 güvenlik yönlendirme kartı — 4 Eylül 2026&apos;da bir klinik
          psikolog tarafından tek tek okundu ve onaylandı. İçerik değiştiğinde
          onay düşüyor ve yeniden inceleme gerekiyor.
        </p>
        <p>
          Bu, Neva&apos;nın bir uzman olduğu anlamına gelmiyor. Anlamı şu: sana
          anlattığı şeyler bir uzmanın &quot;bu doğru ve zararsız&quot; dediği
          şeyler. Sana ne yapman gerektiğini söylemek yine bir uzmanın işi.
        </p>
      </Block>

      <Block heading="Yapay zekâ olduğu açıkça belirtilir">
        <p>
          Neva bir yapay zekâ sistemidir ve bunu hiçbir noktada gizlemez.
          İnsan bir uzman olduğu izlenimi vermez. Her cevabın nasıl üretildiğini
          inceleyebilmen için şeffaflık paneli sunar. Bu yaklaşım Avrupa Birliği
          Yapay Zekâ Yasası&apos;nın şeffaflık ilkeleriyle uyumludur.
        </p>
      </Block>
    </PageShell>
  );
}
