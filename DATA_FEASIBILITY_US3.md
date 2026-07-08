# Veri Fizibilite Araştırması — US3 Evreni İçin Point-in-Time ABD Hisse Verisi (DATA_FEASIBILITY_US3.md)

Tarih: 2026-07-08
Kapsam: **Salt araştırma spike'ı.** Satın alma, kayıt, API anahtarı edinme
YAPILMADI. Kod/config/strateji/tasarım kararı YAPILMADI — bu doküman yalnızca
"böyle bir evren ücretsiz kurulabilir mi, kurulamıyorsa en ucuz güvenilir
ücretli yol nedir" sorusuna kanıta dayalı cevap arar. D2-US ailesi US2
evreninde (bkz. `DATA_AUDIT_US2.md`) mekanik olarak REDDEDİLDİ; olası bir
sonraki adayın ihtiyaç duyacağı evren büyüklüğü (point-in-time, delisted-dahil,
~2005+, ~200+ sembol) burada test edildi. **Hiçbir dondurulmuş/canlı modüle
dokunulmadı** (`strategy/regime_core.py`, `execution/`, `safety/`, `main.py`,
`config/config.yaml`, `data/snapshots/` vb. — tamamı kapsam dışı bırakıldı).
İndirilen tüm test verisi `data/scratch_us3/` altında (gitignore'lu, commit
edilmedi).

---

## (a) Ücretsiz tarihsel S&P 500 üyelik listeleri

İki gerçek aday bulundu; ikisi de aynı kök veriye dayanıyor, biri türev/ayna:

### Aday 1 — `fja05680/sp500` (GitHub) — ANA ADAY

- **İndirildi ve incelendi:** `S&P 500 Historical Components & Changes (Updated).csv`
  → `data/scratch_us3/fja05680_sp500_updated.csv` (2713 satır).
- **Kapsam başlangıcı:** 1996-01-02. Kaynağın kendisi (README) bu ilk dönemi
  Andreas Clenow'un daha eski, bağımsız doğrulanmamış bir dosyasına
  dayandırdığını belirtiyor — **1996-2019 arası ikinci elden, doğrulanmamış
  kabul edilmeli.**
- **Güncellik:** Son satır 2026-06-02; GitHub API'den son commit
  2026-06-09 (`Merge pull request #28 ... Update for 2026-06-08`). Repo aktif
  ve yakın zamanda bakımı yapılıyor.
- **Üyelik değişikliği yoğunluğu:** Dosyada ~2713 tarihli satır (her satır o
  günkü tam bileşen listesi — snapshot formatı, event-log formatı değil).
  Ayrıca `sp500_ticker_start_end.csv` (indirildi, 1256 satır) her ticker için
  index'e giriş/çıkış tarihini ayrı ayrı veriyor; **752 satırda bir çıkış
  tarihi var.**
- **ÖNEMLİ NÜANS (doğrulandı, WebFetch ile README'den):** Ticker adına eklenen
  `-YYYYMM` soneki (örn. `AAMRQ-201312`, `ENRNQ-200411`, `BSC-200805`,
  `LEHMQ-201203`, `WAMUQ-201203`, `WB-200812`, `MER-200812`) **"S&P 500
  index'inden çıkış tarihi" anlamına geliyor — nedeni ayırt etmiyor.** Yani
  hem "şirket iflas etti/tamamen sildi" (Enron, Lehman, Bear Stearns, WaMu)
  hem de "hâlâ yaşıyor ama endeksten düştü/başka endekse geçti" (örn. piyasa
  değeri S&P 400'e düşen bir şirket) aynı sonekle işaretleniyor. Dolayısıyla
  bu dosya tek başına "hangi ticker gerçekten defunct" sorusuna cevap vermiyor
  — sadece point-in-time endeks üyeliğini doğru veriyor (asıl ihtiyaç budur).
  Grep ile doğrulanan örnekler: `ENRNQ-200411`, `LEHMQ-201203`,
  `BSC-200805`, `WAMUQ-201203`, `MER-200812`, `WB-200812` — hepsi dosyada
  mevcut ve tarihleri gerçek olaylarla tutarlı (Enron 2001 iflası sonrası
  tasfiye kaydı 2004'te endeksten silinme, Lehman/Bear/WaMu/Merrill/Wachovia
  2008 krizi ile örtüşüyor).
- **Toplam benzersiz ticker-token sayısı** (tüm tarihler birleşik,
  kaba sayım): 4577. Bunun 468'i `-YYYYMM` sonekli (yani en az bir kez
  endeksten "tarihli" çıkış yapmış).
- **Lisans:** `LICENSE` dosyası MIT (`Copyright (c) 2019-2020 Farrell J.
  Aultman`). Serbestçe kullanılabilir, redistribution engeli yok.
- **Metodoloji dürüstlüğü (README'den alıntı ruhuyla):** Veri Wikipedia'nın
  S&P 500 sayfasından + Google araması ile çapraz kontrolden geliyor; yazar
  kendisi "Wikipedia sadece seçilmiş değişiklikleri gösteriyor, tam liste
  değil" diyor ve elle araştırma ile tamamladığını belirtiyor. İlk ~5 yılda
  sembol sayısı 487-507 bandında (tam 500 değil) — bu normal (S&P 500'de her
  zaman tam 500 hisse yoktur) ama erken dönemde muhtemelen eksik kayıt riski
  de var.

### Aday 2 — `hanshof/sp500_constituents` (GitHub) — TÜREV/AYNA, ANA ADAY DEĞİL

- GitHub API: MIT lisanslı, son commit 2025-08-24 (aktif ama fja05680'den
  daha az sık güncelleniyor).
- README'sinde kendisini `fja05680`'in çıktısını farklı bir formatta
  (her satır = tarih + o tarihteki tam ticker listesi, ayrı `sp500.py` betiği
  ile üretilmiş) sunan bir **ayna/yeniden-paketleme** olarak tanımlıyor —
  bağımsız birincil kaynak değil. `chinobing/historical_sp500_constituents`
  de aynı ailenin başka bir çatalı ("Auto renew" ibaresiyle). Format
  tercihi dışında `fja05680`'e ek doğrulama değeri katmıyor.

**Sonuç (a):** S&P 500 için point-in-time üyelik verisi MIT lisansla,
ücretsiz, aktif bakımlı ve 1996'dan bugüne (2026-06) kadar mevcut. Ancak: (i)
2005 öncesi kısmı ikinci elden/doğrulanmamış, (ii) ticker-çıkış sebebi
(iflas mı, endeks düşüşü mü) ayrıştırılmıyor, (iii) bu sadece **S&P 500 endeks
üyeliği** — fiyat verisi değil (fiyat için bkz. (b)/(c)/(d)).

---

## (b) Delisted/defunct ticker'lar için yfinance testi

`.venv` içinde `yfinance` ile `yf.download(ticker, start="1995-01-01",
end="2026-01-01", auto_adjust=False)` çağrıldı:

| Ticker | Sonuç | Tarih aralığı | Kalite notu |
|---|---|---|---|
| LEH (Lehman Brothers) | **VERİ YOK** | — | `YFPricesMissingError: possibly delisted` |
| BSC (Bear Stearns) | **VERİ YOK** | — | aynı hata |
| WAMUQ (WaMu, iflas-sonrası) | **VERİ YOK** | — | aynı hata |
| ENE (Enron) | **VERİ YOK** | — | aynı hata |
| CIT (CIT Group) | **VERİ YOK** | — | `YFTzMissingError: possibly delisted` |
| BEAR (alternatif dene.) | **VERİ YOK** | — | aynı hata |
| GM (eski General Motors) | **VAR ama YANLIŞ ŞİRKET** | 2010-11-18 → 2025-12-31 (3802 gün) | Bu, 2009 iflasından SONRA IPO edilen "yeni GM" (General Motors Company). Eski GM'in (2009 öncesi, iflasla sıfırlanan) verisi bu ticker altında YOK — yfinance ticker'ı geri dönük olarak eski şirkete bağlamıyor. |
| AIG | **VAR, tam** | 1995-01-03 → 2025-12-31 (7802 gün) | 2009-06/07 1:20 ters bölünmesi çevresinde fiyat serisi düzgün/sürekli (Close kolonu split-adjusted geliyor — `auto_adjust=False` yalnızca temettüyü ayarlamıyor, split'i yine ayarlıyor). Gözle anomali yok. |
| MER (Merrill Lynch) | **VAR ama YANLIŞ ŞİRKET** | yalnız 2025-05-09 → 2025-12-31 (163 gün) | `yf.Ticker("MER").info["longName"]` = **"Meren Energy Inc."** — ticker sembolü geri dönüşüme uğramış, eski Merrill Lynch (2009'da BofA'ya satıldı) verisi YOK. |
| WB (Wachovia) | **VAR ama YANLIŞ ŞİRKET** | 2014-04-17 → 2025-12-31 (2945 gün) | `longName` = **"Weibo Corporation"** — Çinli sosyal medya şirketi. Eski Wachovia (2008'de Wells Fargo'ya satıldı) verisi YOK. |

**Genel bulgu:** yfinance/Yahoo Finance, tamamen tasfiye olmuş (LEH, BSC, ENE,
CIT, WAMUQ) ticker'lar için **hiçbir** geçmiş veri sunmuyor; devralınan/
birleşen şirketler için ise ticker sembolü zamanla başka, ilgisiz bir şirkete
**yeniden atanmış** olabiliyor ve yfinance sessizce o yeni şirketin verisini
döndürüyor (MER, WB, GM örnekleri) — bariz bir hata mesajı yok, sadece yanlış
tarih aralığı/yanlış şirket. Bu, sembol-bazlı toplu indirme yapan bir
pipeline'da **sessiz veri kirliliği** riski demektir: yalnızca tarih aralığı
kontrolü yapmak yeterli değil, `longName`/CIK gibi bir kimlik doğrulaması da
gerekir. AIG gibi "hayatta kalan ama ağır kurumsal aksiyon geçirmiş" örnekte
sorun görülmedi.

---

## (c) Stooq ve Tiingo — anahtarsız yol testi

### Stooq

Bilinen anahtarsız CSV endpoint'i (`https://stooq.com/q/d/l/?s=SYMBOL.US&i=d`)
test edildi (`LEH.US`, `BSC.US`, `ENE.US`, `WAMUQ.US`, `CIT.US`) — hepsi
HTTP 200 döndü ama gövde CSV değil, bir **JavaScript bot-doğrulama
sayfası** (`"This site requires JavaScript to verify your browser"`,
Cloudflare-tarzı challenge script). Sonuç ticker'a özgü değil: canlı ve
sıradan bir ticker olan `AAPL.US`'ta bile aynı engelle karşılaşıldı (tarayıcı
User-Agent'ı taklit etmek de sonucu değiştirmedi). **Bulgu: Stooq'un
anahtarsız CSV indirme endpoint'i, bu test tarihinde (2026-07-08) plain
HTTP istemcisinden (curl) artık erişilebilir değil** — muhtemelen JS
çalıştıran gerçek bir tarayıcı/headless-browser gerektiriyor, bu da
otomatik/scriptlenebilir bir veri hattı için pratik değil (ve headless
tarayıcı kullanmak "anahtarsız API" ruhunun dışına çıkar).

### Tiingo

- Anahtarsız/demo örnek endpoint **bulunamadı** — resmi pricing sayfası
  (`tiingo.com/about/pricing`) hiçbir "signup'sız dene" seçeneği sunmuyor.
- Ücretsiz **Starter** katman ($0/ay) dahi API anahtarı/kayıt gerektiriyor →
  görev kısıtı gereği (anahtar edinme yasak) **test edilmedi.**
- Ücretli **Power** katman: $30/ay bireysel, $50/ay kurumsal-iç-kullanım
  (yıllık: $300 / $499).
- Public dokümantasyonda (EOD API sayfası) delisted-ticker kapsamı veya
  point-in-time endeks üyeliği ile ilgili **açık bir taahhüt bulunamadı**;
  yalnızca genel "corporate action / listing change hatalarını yakalayan
  proprietary temizlik" ifadesi var. Bir AmiBroker forum başlığı ("Tiingo and
  delisted stocks") konuya değiniyor ancak erişim 403 ile engellendi,
  içeriği doğrulanamadı.

**Sonuç (c):** Anahtarsız/ücretsiz-scriptlenebilir yol olarak umulan iki
kapı da (Stooq CSV, Tiingo demo) bu tarihte pratikte kapalı — biri bot
koruması, diğeri hiç var olmayan bir özellik.

---

## (d) Ücretli seçenekler — yalnızca dokümantasyon, deneme/kayıt yok

| Sağlayıcı | Delisted kapsamı iddiası | Point-in-time endeks üyeliği | Yaklaşık fiyat bandı | Lisans notu (solo retail algo trader için) |
|---|---|---|---|---|
| **Norgate Data** (US Stocks, Platinum/Diamond) | EVET — açıkça "Delisted Stocks included at Platinum/Diamond level", ticker'lara `-YYYYMM` soneki (Norgate'in kendi konvansiyonu, fja05680'inkine benzer). Tarihçe 1950'ye kadar iddia ediliyor. | EVET — Platinum/Diamond, herhangi bir (canlı veya delisted) hissenin herhangi bir tarihte bir endeksin üyesi olup olmadığını sorgulama özelliği sunuyor. | Platinum paket: **~$787.50/yıl** (veya $433.13/6 ay) — kaynağa göre değişen tarihsel rakamlar da var (~$630/yıl); kesin güncel fiyat için canlı fiyat hesaplayıcıları var, statik sayfada sabit rakam yok. | EULA (`norgatedata.com/subscribe/eula.php`) — kişisel kullanım için 2 bilgisayarla sınırlı; **redistribution tamamen yasak**; veriyi "finansal bir enstrümanın temeli" ya da "piyasa oluşturma/sağlama" amacıyla kullanmak yasak — bu ifade otomatik trading sistemleri için lisans yorumunu belirsizleştiriyor (net bir "algo trading yasak" cümlesi yok ama "piyasada rekabetçi kullanım" ve "finansal enstrümanın temeli" yasakları geniş yorumlanabilir). Ticari/üçüncü şahıs amaçlı kullanım ayrıca yasak. |
| **Sharadar / Nasdaq Data Link (Core US Equities Bundle, SFA)** | EVET — "Active & Delisted, Point-in-time" olarak pazarlanıyor; fiyat verisi 1998'den, ~20.000+ ABD şirketi. | EVET — S&P 500'e tarihsel eklenme/çıkarılma kayıtları 1957'ye kadar iddia ediliyor. | **Doğrulanamadı** — hem `data.nasdaq.com/databases/SFA/pricing` hem QuantRocket'ın yeniden-satış sayfası fiyatı yalnızca giriş yaptıktan/lisans tipi seçtikten sonra gösteriyor; görev kısıtı gereği giriş/kayıt denenmedi. Sayfa "Professional" (finans sektöründe çalışanlar/başkasının parasını yönetenler) ve "Non-Professional" (bireysel/kişisel kullanım) olarak iki ayrı lisans kademesi olduğunu belirtiyor — ikisi arasındaki somut $ farkı bu araştırmada teyit edilemedi. | Non-Professional / Professional ayrımı mevcut; tam EULA metni bu araştırmada okunmadı (kayıt gerektiriyor). |
| **EODHD** | EVET — ayrı bir "Delisted Data API" ürünü olarak pazarlanıyor. | EVET — ayrı bir "Indices Historical Constituents API" ürünü var (S&P dahil). | En yakın uygun paket **"EOD Historical Data (All World)": $19.99/ay ($199/yıl)**; delisted+intraday'i de kapsayan daha üst paketler $29.99-$99.99/ay bandında (tam olarak hangi paketin delisted+point-in-time-constituents'i birlikte içerdiği bu araştırmada satır satır doğrulanmadı — pricing sayfası paket-özellik matrisini net vermiyor). | Kişisel kullanım standart katmanlarda; ticari kullanım için ayrı "Startups & Enterprise" planına yönlendiriyor. Akademik kullanıma %50 indirim var. Redistribution/algo-trading'e özel bir yasak ibaresi bu araştırmada görülmedi (EULA'nın tamamı okunmadı). |

**Genel gözlem (d):** Üçü de "delisted dahil + point-in-time endeks üyeliği"
iddiasını açıkça yapıyor — bu, (a)+(b)+(c)'de ücretsiz yollarla elde
edilemeyen tam paketi tek kaynaktan sunan tek kategori. Fiyat sıralaması
kabaca: **EODHD en ucuz uygun paket (~$200-300/yıl bandı, ama tam kapsam
matrisi teyitsiz) < Norgate (~$630-790/yıl, kapsam net) < Sharadar (fiyat
görülemedi, community bilgisine göre tarihsel olarak benzer/orta bant, ama bu
araştırmada rakamla doğrulanamadı).**

---

## Sonuç / Bottom-line Verdict

**Soru:** *"2005+ / ~200+ isim / delisted-dahil / point-in-time US evreni
ÜCRETSİZ kurulabilir mi?"*

**Cevap: HAYIR — tam otomatik/güvenilir biçimde, saf ücretsiz kaynaklarla
kurulamıyor.**

Gerekçe:
- **Point-in-time endeks üyeliği** (hangi ticker hangi tarihte S&P 500'de)
  kısmı ÜCRETSİZ ve iyi durumda: `fja05680/sp500` (MIT, 1996-2026, aktif
  bakımlı) bunu sağlıyor — bu parça tek başına EVET.
- Ama **fiyat verisi** tarafında, tamamen tasfiye olmuş/defunct ticker'lar
  (Lehman, Bear Stearns, Enron, WaMu, CIT gibi — tam olarak "point-in-time
  evren" kavramının asıl zorluğu olan grup) için ana ücretsiz kaynak
  (yfinance) **hiç veri döndürmüyor**, ve devralınan şirketlerde ticker
  sembolünün başka bir şirkete yeniden atanması **sessiz veri kirliliği**
  yaratıyor (MER→Meren Energy, WB→Weibo, GM→yeni GM). Anahtarsız alternatif
  olarak umulan Stooq CSV yolu bu tarihte bot-korumasıyla kapalı; Tiingo'nun
  anahtarsız bir yolu hiç yok.
- Sonuç: **iki parça (endeks üyeliği ÜCRETSİZ + defunct-ticker fiyat verisi
  ÜCRETSİZ) birleştirilerek tam bir point-in-time evren inşa edilemiyor** —
  ikinci parça ücretsiz kaynaklarda sistematik olarak eksik/güvenilmez.

**En ucuz güvenilir ücretli yol:** Bulgulara göre **EODHD**'nin "Delisted
Data API" + "Indices Historical Constituents API" içeren paketi, kabaca
**$200-300/yıl** bandında, sağlayıcının kendi iddiasına göre tam kapsamı
(delisted + point-in-time endeks üyeliği) tek abonelikte sunuyor — ancak bu
araştırmada paket-özellik eşleşmesi satır satır doğrulanmadı (yalnızca genel
pricing sayfası okundu, deneme yapılmadı). **Norgate Data** (~$630-790/yıl,
Platinum/Diamond) kapsamı en net dokümante edilmiş seçenek ama daha pahalı
ve lisansı otomatik/algoritmik kullanım açısından bazı belirsiz yasak
ifadeleri içeriyor (redistribution kesin yasak; "finansal enstrümanın temeli"
ve "rekabetçi piyasa kullanımı" yasakları net değil). **Sharadar/Nasdaq Data
Link** kapsam iddiası olarak en güçlülerinden biri (S&P 500 üyeliği 1957'ye
kadar, fiyat 1998'den, delisted dahil) ama bu araştırmada güncel $ fiyatı
görülemedi (giriş gerektiriyor, denenmedi).

---

## HÜKÜM VERME

Bu rapor yalnızca gözlemlenen olguları listeler: hangi kaynak neyi kapsıyor,
hangi tarihte neyin çalışıp çalışmadığı, hangi rakamlar public sayfalarda
görüldü. **Hangi kaynağın seçileceği, ücretli bir aboneliğe girilip
girilmeyeceği, ve US3 evreninin bu bulgularla nasıl tasarlanacağı — bu
raporun kapsamı dışındadır ve kullanıcının/proje sahibinin kararına
bırakılmıştır.** Bu spike hiçbir "şunu yapmalısın" önerisi içermez.
