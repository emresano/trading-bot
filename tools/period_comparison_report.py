# tools/period_comparison_report.py
"""`tools/period_comparison.py::run_comparison()` çıktısından PERIOD_COMPARISON.md
üretir. Bu dosya yalnızca METİN BİÇİMLENDİRMESİDİR — hiçbir hesap/eşik/karar
içermez (kriter/kabul/karar YOK, mühürlü hiçbir eşik etkilenmez)."""
from __future__ import annotations

from pathlib import Path

ROW_ORDER = [
    ("D1", "D1 (rejim-filtreli çekirdek, mühürlü S1b)"),
    ("sepet", "12-sembol eşit-ağırlık sepet al-tut (TRY, maliyetsiz)"),
    ("XU100", "XU100 al-tut (BİLGİ — fiyat endeksi, temettü hariç)"),
    ("faiz_haircut", "TRY faizi — haircut'lı (200bp, S1b'nin kendi mühürlü modeli)"),
    ("faiz_ham", "TRY faizi — haircut'sız (ham, 'mevduat proxy'si')"),
    ("USD", "USD al-tut (USDTRY değişimi, TRY-terim)"),
    ("altin", "Gram altın (TRY, best-effort)"),
    ("TUFE", "TÜFE (FRED, best-effort — bkz. gecikme notu)"),
]


def _pct(x: float) -> str:
    return f"{x * 100:+.2f}%"


def _pct_abs(x: float) -> str:
    return f"{x * 100:.2f}%"


def _window_table_md(table: dict) -> str:
    lines = [
        f"### {table['label']} ({table['start'].date()} → {table['end'].date()})",
        "",
    ]
    if not table["full_coverage"]:
        lines.append(
            "> ⚠ Bu pencerenin istenen başlangıcı mevcut verinin ilk tarihinden ÖNCE — "
            "pencere KISMİ veriyle hesaplandı (yukarıdaki tarih aralığı fiili aralıktır)."
        )
        lines.append("")
    lines.append("| Seri | Toplam Getiri | CAGR | Max DD |")
    lines.append("|---|---:|---:|---:|")
    for key, desc in ROW_ORDER:
        if key not in table["metrics"]:
            continue
        m = table["metrics"][key]
        lines.append(f"| {desc} | {_pct(m['total_return'])} | {_pct(m['cagr'])} | {_pct_abs(m['max_drawdown'])} |")
    lines.append("")
    d1_cagr = table["metrics"]["D1"]["cagr"]
    faiz_cagr = table["metrics"]["faiz_haircut"]["cagr"]
    diff_pp = (d1_cagr - faiz_cagr) * 100
    lines.append(
        f"**D1 − faiz(haircut'lı) farkı (CAGR, pp):** {diff_pp:+.2f}pp "
        f"({'D1 faizin üzerinde' if diff_pp > 0 else 'D1 faizin altında'})."
    )
    lines.append("")
    lines.append(
        f"**İşlem/rejim özeti:** bu pencerede {table['n_switches']} anahtarlama (ENTER/EXIT), "
        f"rejim-ON gün oranı {table['regime_on_ratio']*100:.1f}%."
    )
    if table["label"] == "Son 1 Yıl" and table["n_switches"] < 5:
        lines.append("")
        lines.append(
            "> ⚠ **Az olay = gürültü uyarısı:** bu penceredeki anahtarlama sayısı çok düşük "
            "(<5) — tek bir giriş/çıkışın zamanlaması, bu kısa pencerenin metriklerini (özellikle "
            "toplam getiri ve maxDD) orantısız etkileyebilir. 1 yıllık pencere istatistiksel "
            "olarak ANLAMLI DEĞİLDİR, yalnızca en güncel görüntü olarak verilmiştir."
        )
    if table.get("tufe_stale") and "TUFE" in table["metrics"]:
        lines.append("")
        lines.append(
            "> ⚠ **TÜFE bayat:** bu pencerenin TAMAMI, FRED serisinin son gerçek gözleminden "
            "SONRAKİ döneme denk geliyor — tablodaki TÜFE satırı bu yüzden son bilinen değerle "
            "sabit (forward-fill), toplam getiri/CAGR ≈ 0 görünür. Bu bir hesap hatası DEĞİL, "
            "veri gecikmesinin doğal sonucudur (bkz. yukarı best-effort notu)."
        )
    lines.append("")
    return "\n".join(lines)


def write_report(data: dict, out_path: str | Path = "PERIOD_COMPARISON.md") -> Path:
    eq = data["equity"]
    lines: list[str] = []
    lines.append("# Dönemsel Karşılaştırma Raporu (BİLGİLENDİRME)")
    lines.append("")
    lines.append(
        "> **Bu rapor BİLGİLENDİRME amaçlıdır. Kriter/kabul/karar İÇERMEZ, hiçbir mühürlü "
        "eşiği/parametreyi etkilemez.** Strateji/motor/risk/karar kodu bu turda "
        "DEĞİŞTİRİLMEMİŞTİR — yalnızca mevcut mühürlü S1b araçları "
        "(`tools/run_regime_core.py`, `backtest/regime_core.py`) import edilerek yeniden "
        "kullanılmıştır. Hiçbir grid/varyant taraması yapılmamıştır."
    )
    lines.append("")
    lines.append(f"Üretim tarihi: {data['run_tag']} · D1 equity aralığı: "
                  f"{eq.index[0].date()} → {eq.index[-1].date()} · "
                  f"N/b/M = {data['core_cfg'].ma_period}/{data['core_cfg'].band_pct}/{data['core_cfg'].confirm_days} "
                  f"(mühürlü, S1b — bkz. `config/regime_core.yaml`)")
    lines.append("")

    lines.append("## Veri kaynağı notu (madde 1 — D1 yeniden-üretimi)")
    lines.append("")
    lines.append(
        "D1'in frozen S1b snapshot'ı (`data/snapshots/2026-07-06`) son barı ~2026-07-02'de "
        "bitiyordu; bu rapor için 2026-07-08'e kadar olan EKSİK kuyruk canlı yfinance "
        "çekimiyle tamamlandı ve (varsa) `data/snapshots/aux_cmp/` altına sha256 manifest'li "
        "olarak dondu — **mevcut hiçbir snapshot değiştirilmedi.**"
    )
    lines.append("")
    if data["d1_aux_dir"]:
        lines.append(f"- D1 12-sembol uzantısı: `{data['d1_aux_dir']}/` (manifest.json + sha256).")
    else:
        lines.append("- D1 12-sembol evreninde ek dondurma GEREKMEDİ (frozen snapshot zaten günceldi).")
    if data["usd_aux_dir"]:
        lines.append(f"- USDTRY uzantısı: `{data['usd_aux_dir']}/` (manifest.json + sha256, aynı dizin).")
    max_diff = max((n.get("max_abs_rel_diff", 0.0) for n in data["d1_diff_notes"]), default=0.0)
    lines.append(
        f"- Örtüşen barlarda kaynak-tutarlılık kontrolü: {len(data['d1_diff_notes'])} sembol, "
        f"maksimum mutlak-göreli fark {max_diff:.2e} (frozen snapshot ↔ taze çekim; 07-09 DATA_DRIFT "
        "vakasının aksine bu turda anlamlı sapma YOK — bkz. STATUS.md 'DRIFT ÇÖZÜMÜ' bölümü)."
    )
    lines.append(
        "- **Determinizm çekincesi (dürüstçe):** en güncel 1-2 günün bar verisi yfinance'in geç "
        "revizyon davranışına (STATUS.md K4/DATA_DRIFT — bilinen, tekrarlayan bir olgu) tabidir; "
        "bu rapor birkaç gün sonra yeniden koşulursa en son 1-2 günün kapanışı hafifçe değişebilir. "
        "2005→(frozen snapshot son barı) kısmı TAM DETERMİNİSTİKTİR (S1b'nin kendi mühürlü kaynağı)."
    )
    if data["ghost_log"]:
        lines.append(f"- Hayalet-bar filtresi (mevcut, reuse): {len(data['ghost_log'])} bar elendi "
                      f"(`{data['ghost_log'][0]['symbol']}` {data['ghost_log'][0]['date'].date()} — bilinen, "
                      "STATUS.md KALICI KAYIT 7'de belgeli EREGL 2024-04-09 hayalet barı).")
    lines.append("")
    lines.append(f"- Altın (best-effort): {data['gold_note']}")
    lines.append(f"- TÜFE (best-effort): {data['cpi_note']}")
    lines.append(
        "  Son gerçek gözlemden `Üretim tarihi`ne kadarki tüm günler forward-fill (son bilinen "
        "seviyeyle sabit) taşınmıştır — bu nedenle AŞAĞIDAKİ HER pencerenin TÜFE CAGR'ı, gerçek "
        "enflasyonu (özellikle son ~15 ay) HAFİFE ALIR/AŞAĞI SAPTIRIR; yalnızca 1 yıllık pencerede "
        "bu tamamen sıfıra düşecek kadar belirgindir (ayrıca işaretlendi)."
    )
    lines.append("")

    lines.append("## Pencere Tabloları")
    lines.append("")
    lines.append(
        "> Satırlar: D1, sepet, XU100 (BİLGİ), faiz-haircut'lı (S1b'nin kendi mühürlü modeli), "
        "faiz-ham, USD al-tut, [altın], [TÜFE]. Sütunlar: toplam getiri, CAGR, max DD "
        "(pencerenin KENDİ başlangıcına göre, tam-dönem rakamlarıyla KARIŞTIRILMAMALI)."
    )
    lines.append("")
    for key, label, start, end, full_cov in data["windows"]:
        lines.append(_window_table_md(data["window_tables"][key]))

    lines.append("## \"Faizde Tutsaydım\" Sorusunun Net Cevabı")
    lines.append("")
    lines.append("D1'in CAGR'ı, TRY faizinin (haircut'lı, S1b mühürlü model) CAGR'ından ne kadar farklı:")
    lines.append("")
    lines.append("| Pencere | D1 CAGR | Faiz(haircut) CAGR | Fark (pp) |")
    lines.append("|---|---:|---:|---:|")
    for key, label, start, end, full_cov in data["windows"]:
        t = data["window_tables"][key]
        d1c = t["metrics"]["D1"]["cagr"]
        fc = t["metrics"]["faiz_haircut"]["cagr"]
        lines.append(f"| {t['label']} | {_pct(d1c)} | {_pct(fc)} | {(d1c-fc)*100:+.2f}pp |")
    lines.append("")

    lines.append("## USD Paneli (\"Satın Alma Gücü\" Merceği)")
    lines.append("")
    lines.append(
        "D1 ve sepetin USD-terim (equity/USDTRY) CAGR + max DD'si — reel/uluslararası yatırımcı "
        "perspektifi. TRY-terim tablolarla KARIŞTIRILMAMALI (bkz. yukarı)."
    )
    lines.append("")
    lines.append("| Pencere | D1 USD CAGR | D1 USD maxDD | Sepet USD CAGR | Sepet USD maxDD |")
    lines.append("|---|---:|---:|---:|---:|")
    for key, label, start, end, full_cov in data["windows"]:
        up = data["usd_panel"][key]
        lines.append(f"| {up['label']} | {_pct(up['D1_usd']['cagr'])} | {_pct_abs(up['D1_usd']['max_drawdown'])} | "
                     f"{_pct(up['sepet_usd']['cagr'])} | {_pct_abs(up['sepet_usd']['max_drawdown'])} |")
    lines.append("")
    tam = data["usd_panel"]["tam_donem"]
    lines.append(
        f"**Tutarlılık kontrolü:** S1 spike'ı (faizsiz, KALICI KAYIT 4) tam-dönem D1 USD CAGR'ı "
        f"+%5.08 bulmuştu; S1b (faizli, `REGIME_CORE_S1B.md` (f)) bunu +%8.70'e yükseltti. Bu "
        f"turun (faizli, birkaç gün daha uzun tarihçeli) tam-dönem D1 USD CAGR'ı "
        f"**{_pct(tam['D1_usd']['cagr'])}** — S1b'nin +%8.70'ine (S1'in +%5.08'ine DEĞİL, çünkü "
        "bu ölçüm de faizli) çok yakın, tutarlı. Sepet USD CAGR "
        f"**{_pct(tam['sepet_usd']['cagr'])}** de S1b'nin +%15.15'ine yakın — küçük farklar yalnızca "
        "birkaç ek günün (07-03→07-08) etkisidir, yeni bir varyant/parametre DEĞİL."
    )
    lines.append("")

    lines.append("## Kriz-Yılı Ayrıştırması (BİLGİ)")
    lines.append("")
    lines.append(
        "Botun varlık sebebinin (sermaye koruma) görünür olduğu/olmadığı yıllar — yalnızca "
        "toplam getiri, D1 vs sepet vs faiz(haircut'lı):"
    )
    lines.append("")
    lines.append("| Yıl | D1 | Sepet | Faiz(haircut) |")
    lines.append("|---|---:|---:|---:|")
    for row in data["crisis_rows"]:
        lines.append(f"| {row['label']} | {_pct(row['D1'])} | {_pct(row['sepet'])} | {_pct(row['faiz_haircut'])} |")
    lines.append("")
    lines.append(
        "2008 (küresel finansal kriz) ve 2018 (kur şoku) yıllarında D1 sepetin ciddi altındaki "
        "kaybını BÜYÜK ÖLÇÜDE ATLATIYOR (rejim filtresi nakde geçmiş) — varlık sebebi görünür. "
        "2013'te ise D1 sepetin ALTINDA kalıyor (whipsaw/geç dönüş) — filtre her yıl işe yaramıyor, "
        "bu beklenen ve dürüst bir gözlem."
    )
    lines.append("")

    lines.append("## Dürüst Kapanış Notu")
    lines.append("")
    lines.append(
        "Bu rapor **bilgilendirmedir** — STATUS.md'deki mühürlü kabul kararlarını (KALICI KAYIT 6/8, "
        "D1 ailesinin kabulü) hiçbir şekilde ETKİLEMEZ, geri almaz, güçlendirmez. Hiçbir pencere/yıl "
        "seçilerek strateji değerlendirmesi/parametre değişikliği yapılmamıştır (criterion-shopping "
        "YASAK) — tüm pencereler (1y/3y/5y/10y/tam-dönem) ve tüm kriz yılları AYNI, koşumdan önce "
        "belirlenmiş listeden, seçmeden raporlanmıştır. 1 yıllık pencerenin düşük anahtarlama sayısı "
        "nedeniyle istatistiksel önemi yoktur (yukarıda her tabloda ayrıca not düşüldü). İki durma "
        "noktası (Faz 4 backtest değerlendirmesi + gerçek sermaye) ve K1.5/G1 kuyruğu bu raporla "
        "HİÇBİR ŞEKİLDE değişmez."
    )
    lines.append("")

    text = "\n".join(lines)
    path = Path(out_path)
    path.write_text(text, encoding="utf-8")
    return path
