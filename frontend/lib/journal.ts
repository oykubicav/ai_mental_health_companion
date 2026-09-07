// Günlük için ortak sabitler ve tarih yardımcıları.
//
// Tarih sunucuda değil burada belirleniyor: "bugün" kullanıcının saat
// diliminde ne ise o. UTC'ye bakılsa gece yazan kullanıcı bir sonraki
// güne düşerdi.

export interface JournalTag {
  id: string;
  label: string;
  group: "gun" | "his";
}

export const JOURNAL_TAGS: JournalTag[] = [
  { id: "uyku_iyi", label: "İyi uyudum", group: "gun" },
  { id: "uyku_kotu", label: "Kötü uyudum", group: "gun" },
  { id: "hareket", label: "Hareket ettim", group: "gun" },
  { id: "disari_ciktim", label: "Dışarı çıktım", group: "gun" },
  { id: "insanlarla", label: "İnsanlarlaydım", group: "gun" },
  { id: "yalniz_kaldim", label: "Yalnız kaldım", group: "gun" },
  { id: "is_yogun", label: "İş yoğundu", group: "gun" },
  { id: "dinlendim", label: "Dinlendim", group: "gun" },
  { id: "kaygi", label: "Kaygı", group: "his" },
  { id: "huzun", label: "Hüzün", group: "his" },
  { id: "ofke", label: "Öfke", group: "his" },
  { id: "umut", label: "Umut", group: "his" },
];

export const MOODS: { value: number; label: string }[] = [
  { value: 1, label: "Çok zor" },
  { value: 2, label: "Zor" },
  { value: 3, label: "Orta" },
  { value: 4, label: "İyi" },
  { value: 5, label: "Çok iyi" },
];

export function tagLabel(id: string): string {
  return JOURNAL_TAGS.find((t) => t.id === id)?.label ?? id;
}

/** Yerel saate göre YYYY-AA-GG. toISOString UTC'ye çevirdiği için kullanılmıyor. */
export function isoDate(d: Date): string {
  const ay = String(d.getMonth() + 1).padStart(2, "0");
  const gun = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${ay}-${gun}`;
}

export function bugun(): string {
  return isoDate(new Date());
}

export function gunKaydir(iso: string, delta: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(y, m - 1, d);
  t.setDate(t.getDate() + delta);
  return isoDate(t);
}

/** "7 Eylül Pazartesi" — bugün ve dün için kelimeye çevirir. */
export function gunBasligi(iso: string): string {
  if (iso === bugun()) return "Bugün";
  if (iso === gunKaydir(bugun(), -1)) return "Dün";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    weekday: "long",
  });
}

export function kisaTarih(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
  });
}

/** Son 14 günün tarihleri, eskiden yeniye. */
export function sonGunler(n = 14): string[] {
  const out: string[] = [];
  for (let i = n - 1; i >= 0; i--) out.push(gunKaydir(bugun(), -i));
  return out;
}
