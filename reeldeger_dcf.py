"""
REELDEĞER — DCF Hesap Motoru
Kaynak: pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/dcfallOld.pdf

Damodaran Slayt referansları kod içinde belirtilmiştir.
"""

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# DAMODARAN PARAMETRELERİ
# ctryprem.html — Şubat 2026 güncelleme
# ─────────────────────────────────────────────────────────────────────────────
PARAMETRELER = {
    "rf":                3.96,   # ABD T-Bond − ABD default spread
    "erp":               4.23,   # Olgun Piyasa ERP (Ocak 2026)
    "crp":               4.66,   # Türkiye CRP — Ba3 rating (Şubat 2026)
    "tr_default_spread": 3.06,   # Türkiye default spread (Kd için)
    "vergi":             0.25,   # Türkiye kurumlar vergisi
    "stable_g":          2.50,   # Terminal büyüme — USD nominal
    "arge_omur":         5,      # Ar-Ge amortisman ömrü (Slayt 76)
}

# Finansal şirketler — FCFF uygulanamaz (Damodaran spreadsh.htm)
FINANSAL_SEKTORLER = {
    "Aracı Kurumlar", "Menkul Kıymet Yat. Ort.", "Faktoring",
    "Finansal Kiralama", "Finansman Şirketleri", "Girişim Sermayesi Yat. Ort.",
    "Yatırım Şirketleri", "Bankacılık", "Sigorta",
}

MIN_SEKTOR_SIRKET = 5   # Sektör ortalaması için minimum şirket sayısı


def _sf(val) -> float:
    """Güvenli float dönüşümü."""
    try:
        v = float(val)
        return 0.0 if (v != v) else v
    except (TypeError, ValueError):
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# FİNANSAL ŞİRKET TESPİTİ
# Damodaran: Financial Service firms → DDM, not FCFF
# Kural: Finansal Borç / Aktif > %40
# ─────────────────────────────────────────────────────────────────────────────

def finansal_mi(row) -> bool:
    aktif    = _sf(row.get("Aktifler"))
    fin_borc = _sf(row.get("Finansal Borçlar"))
    ozkaynak = max(_sf(row.get("Özkaynaklar")), 1.0)
    if aktif > 0 and fin_borc / aktif > 0.40:
        return True
    if fin_borc / ozkaynak > 4.0:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# FİNTABLES YÜKLEME
# Fintables USD Excel: Ar-Ge (5 yıl) + Ticari Borçlar
# ─────────────────────────────────────────────────────────────────────────────

def fintables_yukle(dosya) -> dict:
    """
    Returns: {ticker: {"ticari_borc": float, "arge": [t, t-1, t-2, t-3, t-4]}}
    Arge değerleri USD, pozitif (gider olarak geliyorsa abs alınır).
    """
    try:
        df = pd.read_excel(dosya)
    except Exception:
        return {}

    sonuc = {}
    for _, row in df.iterrows():
        kod = str(row.get("Sirket", row.get("Şirket", ""))).strip()
        if not kod:
            continue

        ticari = abs(_sf(row.get("Ticari Borclar (2025/12, USD)",
                          row.get("Ticari Borçlar (2025/12, USD)", 0))))

        arge_yillar = []
        for yil in ["2025", "2024", "2023", "2022", "2021"]:
            v = _sf(row.get(f"Arge Giderleri ({yil}/12, USD)",
                    row.get(f"Ar-Ge Giderleri ({yil}/12, USD)", 0)))
            arge_yillar.append(abs(v))

        sonuc[kod] = {"ticari_borc": ticari, "arge": arge_yillar}

    return sonuc


# ─────────────────────────────────────────────────────────────────────────────
# AR-GE RESEARCH ASSET AKTİFLEŞTİRME
# Damodaran Slayt 76-77 — Cisco örneğiyle doğrulandı
#
# Research Asset = Σ unamortize Ar-Ge
#   R[0]*1.0 + R[1]*0.8 + R[2]*0.6 + R[3]*0.4 + R[4]*0.2
#   (Cisco: 3,035 ✓)
#
# Amortisman = Σ (geçmiş yıllar / 5)  — cari yıl henüz başlamadı
#   (Cisco: 484.6; 5 yıllık veriyle yaklaşım: 466.8)
#
# Düzeltme FVÖK = Ar-Ge(cari) − Amortisman
#   (Cisco: ~1,109 ✓)
#
# Slayt 86: Adjusted Net CapEx = Net CapEx + Ar-Ge(cari) − Amortisman
# Slayt 78: Research Asset → kapital tabanına eklenir (ROC paydası)
# ─────────────────────────────────────────────────────────────────────────────

ARGE_AGIRLIKLAR = [1.00, 0.80, 0.60, 0.40, 0.20]

def arge_hesapla(arge_yillar: list) -> dict:
    if not arge_yillar or all(v == 0 for v in arge_yillar):
        return {"research_asset": 0.0, "amortizasyon": 0.0,
                "arge_cari": 0.0, "duzeltme": 0.0, "var": False}

    n = min(len(arge_yillar), len(ARGE_AGIRLIKLAR))

    research_asset = sum(arge_yillar[i] * ARGE_AGIRLIKLAR[i] for i in range(n))
    # Amortisman: index 0 (cari yıl) dahil edilmez
    amortizasyon   = sum(arge_yillar[i] / 5 for i in range(1, n))
    arge_cari      = arge_yillar[0]
    duzeltme       = arge_cari - amortizasyon

    return {
        "research_asset": research_asset,
        "amortizasyon":   amortizasyon,
        "arge_cari":      arge_cari,
        "duzeltme":       duzeltme,
        "var":            arge_cari > 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC RATING — Kd
# Damodaran Slayt 53-56
#
# Coverage = Düzeltilmiş FVÖK / Finansman Giderleri
# Kd pretax = Rf + Türkiye Default Spread + Şirket Default Spread
# Kd aftertax = Kd pretax × (1 − vergi)
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_SPREAD = [
    (8.50, float("inf"), 0.75),   # AAA
    (6.50, 8.50,         1.00),   # AA
    (5.50, 6.50,         1.50),   # A+
    (4.25, 5.50,         1.80),   # A
    (3.00, 4.25,         2.00),   # A-
    (2.50, 3.00,         2.25),   # BBB
    (2.00, 2.50,         3.50),   # BB
    (1.75, 2.00,         4.75),   # B+
    (1.50, 1.75,         6.50),   # B
    (1.25, 1.50,         8.00),   # B-
    (0.80, 1.25,        10.00),   # CCC
    (0.65, 0.80,        11.50),   # CC
    (0.20, 0.65,        12.70),   # C
    (0.00, 0.20,        15.00),   # D
]

def kd_hesapla(fvok_duz: float, fin_gider: float, D: dict) -> tuple:
    """
    Slayt 53: Coverage = EBIT / Interest Expenses → Rating → Spread
    Slayt 55: Kd = Rf + Country Spread + Company Spread
    """
    if not fin_gider or fin_gider <= 0:
        # Borçsuz şirket → AAA
        spread   = 0.75
        coverage = 999.0
    elif fvok_duz <= 0:
        # Negatif FVÖK → D
        spread   = 15.0
        coverage = 0.0
    else:
        coverage = fvok_duz / abs(fin_gider)
        spread   = 15.0
        for alt, ust, s in COVERAGE_SPREAD:
            if alt <= coverage < ust:
                spread = s
                break

    kd_pre = D["rf"] + D["tr_default_spread"] + spread
    return kd_pre, kd_pre * (1 - D["vergi"]), spread, coverage


# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL DEĞER
# Damodaran Slayt 142-144
#
# Stable büyümede: ROC → WACC (excess return = 0)
# Terminal Reinv Rate = stable_g / WACC
# Terminal FCFF = NOPAT_terminal × (1 − Terminal Reinv)
# TV = Terminal FCFF / (WACC − g)
# ─────────────────────────────────────────────────────────────────────────────

def terminal_deger(nopat_y5: float, wacc_d: float, g_s: float) -> tuple:
    term_roc   = wacc_d                        # Slayt 142: ROC → WACC
    term_reinv = g_s / term_roc               # Slayt 144
    term_nopat = nopat_y5 * (1 + g_s)
    term_fcff  = term_nopat * (1 - term_reinv)
    tv         = term_fcff / (wacc_d - g_s)
    return tv, term_roc, term_reinv, term_fcff


# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA — SEKTÖR BAZINDA
# Damodaran Slayt 33
#
# λ = Firma yurtiçi gelir oranı / Sektör ortalama yurtiçi gelir oranı
# Embraer örneği: %35 / %70 = 0.50
# ─────────────────────────────────────────────────────────────────────────────

def sektor_ortalamalari_hesapla(df: pd.DataFrame) -> dict:
    """BIST'teki tüm şirketlerden sektör bazında yurtiçi oran ortalaması hesapla."""
    sektor_data = {}
    tum = []

    if "Hisse Sektör" not in df.columns or "Yurt İçi Satışlar" not in df.columns:
        return {"__BIST__": 0.546}

    for sektor, grup in df.groupby("Hisse Sektör"):
        if sektor in FINANSAL_SEKTORLER:
            continue
        oranlar = []
        for _, r in grup.iterrows():
            try:
                yi = float(r.get("Yurt İçi Satışlar", 0) or 0)
                ns = float(r.get("Net Satışlar (Yıllık)", 0) or 0)
                if ns > 0:
                    o = yi / ns
                    if 0.0 <= o <= 1.0:
                        oranlar.append(o)
                        tum.append(o)
            except Exception:
                pass
        if len(oranlar) >= MIN_SEKTOR_SIRKET:
            sektor_data[sektor] = float(np.mean(oranlar))

    sektor_data["__BIST__"] = float(np.mean(tum)) if tum else 0.546
    return sektor_data


def lambda_hesapla(yurtici, net_satis, sektor, sektor_ort) -> tuple:
    """Slayt 33: λ = Firma% / Sektör%"""
    if not net_satis or net_satis <= 0:
        return 1.0, sektor_ort.get("__BIST__", 0.546), "veri_yok"

    firma_oran = max(min(yurtici / net_satis, 1.0), 0.0)
    if sektor and sektor in sektor_ort:
        payda  = sektor_ort[sektor]
        kaynak = f"sektör ({sektor})"
    else:
        payda  = sektor_ort.get("__BIST__", 0.546)
        kaynak = "BIST genel"

    payda = max(payda, 0.01)
    lam   = max(min(firma_oran / payda, 2.0), 0.0)
    return lam, payda, kaynak


# ─────────────────────────────────────────────────────────────────────────────
# ROC
# Damodaran Slayt 126:
# ROC = NOPAT / (BV of Debt + BV of Equity)
# "Debt" = Finansal Borç (financial debt, not trade payables)
#
# Slayt 78: Research Asset kapital tabanına eklenir
# ─────────────────────────────────────────────────────────────────────────────

def roc_hesapla(nopat, fin_borc, ozkaynak, research_asset=0.0) -> float:
    kapital = max(fin_borc + ozkaynak + research_asset, 1.0)
    return nopat / kapital   # Negatif ROC da mümkün (Slayt 129)


# ─────────────────────────────────────────────────────────────────────────────
# FVÖK NORMALİZASYON KONTROLÜ
# Damodaran Slayt 79-80
# Finansal gelirler (yatırım fonu, forward kârı vs) faaliyet geliri değil
# ─────────────────────────────────────────────────────────────────────────────

def fvok_normalize_kontrol(fvok, fin_gelir) -> dict:
    if fin_gelir and fvok and fvok > 0:
        oran = abs(fin_gelir) / abs(fvok)
        if oran > 0.20:
            return {
                "uyari": True,
                "mesaj": (f"⚠ Finansman Gelirleri FVÖK'ün %{oran*100:.0f}'i "
                          "— Slayt 79: Tek seferlik finansal gelir olabilir. "
                          "Faaliyet raporu kontrol edin.")
            }
    return {"uyari": False, "mesaj": ""}


# ─────────────────────────────────────────────────────────────────────────────
# ANA DCF FONKSİYONU
# Damodaran 2-Stage FCFF Valuation
#
# WACC Borcu:
#   Damodaran Slayt 57: "Market value weights for DEBT and equity."
#   DEBT = finansal borç (Finansal Borçlar)
#   Ticari borç, vergi borcu vb. WACC borcuna GİRMEZ
#   NOT: Fastweb "Finansal Borçlar" TFRS 16 kira yükümlülüğünü içerir.
#   Bu nedenle ayrıca kira girişi YAPILMAZ (çifte sayma olur).
#
#   Slayt 57: "The debt subtracted from firm value = same debt in WACC"
#
# Büyüme:
#   Damodaran Slayt 116: g = Reinv Rate × ROC
#   Slayt 139: Stable growth can be NEGATIVE — alt sınır YOKTUR
#   Slayt 126: Reinv Rate = (Net CapEx + ΔNWC) / NOPAT
#
# Negatif FVÖK:
#   Damodaran Slayt 81: Normalize edilmeden değerleme yapılmaz
# ─────────────────────────────────────────────────────────────────────────────

def dcf_hesapla(row, D=None, ft_row=None) -> dict:
    """
    Parametreler:
      row    — Fastweb satırı (pd.Series veya dict)
      D      — Damodaran parametreleri
      ft_row — Fintables verisi {"ticari_borc": float, "arge": list}
    """
    if D is None:
        D = PARAMETRELER
    if ft_row is None:
        ft_row = {}

    # Finansal şirket kontrolü
    if finansal_mi(row):
        return {"hata": "finansal", "karar": "—"}

    # ── Ham veriler (Fastweb) ─────────────────────────────────────────────────
    beta      = _sf(row.get("Beta")) or 0.95
    fvok_ham  = _sf(row.get("Esas Faaliyet Karı /Zararı Net (Yıllık)"))
    amort     = _sf(row.get("Amortismanlar (Yıllık)"))
    capex_ham = abs(_sf(row.get("Yatırım Faaliyetlerinden Kaynaklanan Nakit Akışlar")))
    fin_borc  = _sf(row.get("Finansal Borçlar"))   # Slayt 57: WACC borcu
    ozkaynak  = max(_sf(row.get("Özkaynaklar")), 1.0)
    pd_val    = _sf(row.get("Piyasa Değeri")) or ozkaynak
    nakit     = _sf(row.get("Nakit ve Nakit Benzerleri"))
    net_satis = max(_sf(row.get("Net Satışlar (Yıllık)")), 1.0)
    donen_v   = _sf(row.get("Dönen Varlıklar"))
    kv_borc   = _sf(row.get("Kısa Vadeli Borçlar"))
    yurtici   = _sf(row.get("Yurt İçi Satışlar"))
    sektor    = str(row.get("Hisse Sektör", "") or "")
    fin_gelir = _sf(row.get("Finansman Gelirleri"))
    fin_gider = _sf(row.get("Finansman Giderleri"))
    fiyat     = _sf(row.get("Hisse Kapanış"))

    # ── Fintables verileri ────────────────────────────────────────────────────
    ticari_borc = abs(_sf(ft_row.get("ticari_borc"))) if ft_row else 0.0
    arge_yillar = ft_row.get("arge", []) if ft_row else []

    # ── AR-GE AKTİFLEŞTİRME (Slayt 76-77) ───────────────────────────────────
    arge = arge_hesapla(arge_yillar)

    # Düzeltilmiş FVÖK = FVÖK + Ar-Ge(cari) − Amortisman
    fvok = fvok_ham + arge["duzeltme"]

    # ── NEGATİF FVÖK KONTROLÜ (Slayt 81) ─────────────────────────────────────
    # Negatif kazanç normalize edilmeden değerleme yapılamaz
    if fvok <= 0:
        return {
            "hata": "negatif_fvok",
            "karar": "—",
            "fvok_ham": fvok_ham,
            "fvok": fvok,
            "arge_duzeltme": arge["duzeltme"],
            "mesaj": (
                f"FVÖK = {fvok:,.0f} USD (negatif veya sıfır). "
                "Damodaran Slayt 81: Negatif kazanç normalize edilmeden "
                "FCFF değerlemesi yapılamaz."
            )
        }

    # ── FVÖK NORMALİZASYON KONTROLÜ (Slayt 79-80) ────────────────────────────
    fvok_kontrol = fvok_normalize_kontrol(fvok, fin_gelir)

    # ── LAMBDA (Slayt 33) ─────────────────────────────────────────────────────
    sektor_ort = D.get("sektor_ort", {"__BIST__": 0.546})
    lam, lam_payda, lam_kaynak = lambda_hesapla(yurtici, net_satis, sektor, sektor_ort)

    # ── Ke = Rf + β×ERP + λ×CRP (Slayt 34) ──────────────────────────────────
    ke = D["rf"] + beta * D["erp"] + lam * D["crp"]

    # ── Kd SYNTHETIC RATING (Slayt 53-56) ────────────────────────────────────
    kd_pretax, kd_aftertax, sirket_spread, coverage = kd_hesapla(fvok, fin_gider, D)

    # ── WACC — Market Value ağırlıkları (Slayt 57) ────────────────────────────
    # DEBT = Finansal Borçlar (banka kredileri + tahvil + TFRS 16 kira)
    # KV/UV Borç KULLANILMAZ — ticari borç, vergi vs. içerir
    top_borc  = fin_borc
    toplam_mv = top_borc + pd_val
    w_eq   = pd_val   / toplam_mv if toplam_mv > 0 else 0.70
    w_debt = top_borc / toplam_mv if toplam_mv > 0 else 0.30
    wacc   = ke * w_eq + kd_aftertax * w_debt
    wacc_d = wacc / 100
    g_s    = D["stable_g"] / 100

    if wacc_d <= g_s:
        return {"hata": "wacc_dusuk", "wacc": wacc, "karar": "—",
                "ke": ke, "kd_pretax": kd_pretax}

    # ── NOPAT ─────────────────────────────────────────────────────────────────
    nopat = fvok * (1 - D["vergi"])

    # ── NWC (Slayt 89-91) ─────────────────────────────────────────────────────
    # Damodaran Slayt 89 tam tanım:
    # NWC = Non-cash current assets − Non-debt current liabilities
    #     = (Stoklar + Ticari Alacaklar) − Ticari Borçlar
    #
    # Non-cash CA: Dönen Varlık - Nakit YANLIŞ
    #              Stoklar + Ticari Alacaklar DOĞRU (Slayt 89)
    # Non-debt CL: Ticari Borçlar DOĞRU (accounts payable)
    # Slayt 91: NWC negatifse sıfır al
    stoklar         = _sf(row.get("Stoklar"))
    ticari_alacak   = _sf(row.get("Ticari Alacaklar"))

    if stoklar > 0 and ticari_alacak > 0 and ticari_borc > 0:
        # Tam Damodaran (Slayt 89)
        nwc        = max((stoklar + ticari_alacak) - ticari_borc, 0)
        nwc_kaynak = "stoklar+alacaklar-ticari_borc"
    elif stoklar > 0 and ticari_alacak > 0:
        # Ticari Borç eksik — non-debt CL tahmini
        nwc        = max(stoklar + ticari_alacak, 0)
        nwc_kaynak = "stoklar+alacaklar (ticari_borc eksik)"
    elif ticari_borc > 0:
        # Stok/Alacak eksik — eski yaklaşım
        nwc        = max((donen_v - nakit) - ticari_borc, 0)
        nwc_kaynak = "donen-nakit-ticari_borc (tahmini)"
    else:
        # Hiçbir ek veri yok — en kaba yaklaşım
        nwc        = max((donen_v - nakit) - kv_borc, 0)
        nwc_kaynak = "donen-nakit-kv_borc (tahmini)"
    nwc_oran = nwc / net_satis if net_satis > 0 else 0.0

    # ── ROC (Slayt 126 + 78) ─────────────────────────────────────────────────
    roc = roc_hesapla(nopat, fin_borc, ozkaynak, arge["research_asset"])

    # ── Reinvestment Rate (Slayt 126) ─────────────────────────────────────────
    # Net CapEx düzeltilmiş: Ar-Ge dahil (Slayt 86)
    capex_duz  = capex_ham + arge["arge_cari"] - arge["amortizasyon"]
    net_capex  = capex_duz - amort   # Negatif olabilir (amortisman > yatırım)

    # ΔNWC için iteratif yaklaşım:
    # Adım 1: Net CapEx bazında ilk g tahmini
    reinv_0  = net_capex / nopat if nopat > 0 else 0.0
    g_0      = max(reinv_0 * roc, 0.0)  # g_0 negatif olmamalı (tahmini)

    # Adım 2: İlk g ile ΔNWC tahmini
    delta_nwc_est = nwc_oran * g_0 * net_satis

    # Adım 3: Nihai Reinvestment Rate (Slayt 126)
    reinv_rate = (net_capex + delta_nwc_est) / nopat

    # ── g = Reinv Rate × ROC (Slayt 116) ─────────────────────────────────────
    # Damodaran Slayt 139: "Stable growth can be negative" → alt sınır YOK
    # Üst sınır yok (Damodaran yüksek büyüme şirketleri için kısıtlamıyor)
    g_fund = reinv_rate * roc
    buyume = g_fund   # Ham Damodaran değeri, sınır uygulanmıyor

    # ── FCFF (Slayt 66) ───────────────────────────────────────────────────────
    # FCFF = EBIT(1-t) − Net CapEx − ΔNWC
    delta_nwc_f = nwc_oran * buyume * net_satis if buyume > 0 else 0.0
    fcff = nopat - net_capex - delta_nwc_f

    # ── 5 Yıl Projeksiyon ─────────────────────────────────────────────────────
    pv_fcff = 0.0
    proj    = []
    for t in range(1, 6):
        f  = fcff * (1 + buyume) ** t
        pv = f    / (1 + wacc_d) ** t
        pv_fcff += pv
        proj.append({"Yıl": 2025 + t, "FCFF": f, "PV": pv})

    # ── Terminal Değer (Slayt 142-144) ────────────────────────────────────────
    nopat_y5 = nopat * (1 + buyume) ** 5
    tv, term_roc, term_reinv, term_fcff = terminal_deger(nopat_y5, wacc_d, g_s)
    pv_tv = tv / (1 + wacc_d) ** 5

    # ── Firma Değeri → Özsermaye (Slayt 153) ─────────────────────────────────
    # + Nakit (non-operating asset, ayrı eklenir)
    # − Finansal Borç (Slayt 57: aynı borç WACC'ta kullanılan)
    firma_deg = pv_fcff + pv_tv + nakit
    oz_deg    = firma_deg - top_borc

    # ── Hisse Başına İçsel Değer ──────────────────────────────────────────────
    hs    = (pd_val / fiyat) if fiyat > 0 and pd_val > 0 else 1.0
    icsel = oz_deg / hs if hs > 0 else 0.0
    iskonto = ((icsel - fiyat) / icsel * 100) if fiyat > 0 and icsel > 0 else None

    # ── Karar ─────────────────────────────────────────────────────────────────
    karar = "İZLE"
    if iskonto is not None:
        if   iskonto > 20:   karar = "GİRİŞ"
        elif iskonto < -10:  karar = "ÇIKIŞ"

    return {
        # Sonuç
        "karar":   karar,
        "iskonto": iskonto,
        "icsel":   icsel,
        "fiyat":   fiyat,

        # Ke bileşenleri
        "ke":           ke,
        "lam":          lam,
        "lam_payda":    lam_payda,
        "lam_kaynak":   lam_kaynak,
        "sektor":       sektor,
        "beta":         beta,

        # Kd bileşenleri
        "kd_pretax":    kd_pretax,
        "kd_aftertax":  kd_aftertax,
        "sirket_spread": sirket_spread,
        "coverage":     coverage,

        # WACC
        "wacc":    wacc,
        "w_equity": w_eq,
        "w_debt":   w_debt,
        "top_borc": top_borc,   # = Finansal Borç (Slayt 57)

        # Büyüme
        "roc":       roc,
        "reinv_rate": reinv_rate,
        "g_fund":    g_fund,
        "buyume":    buyume,

        # FCFF
        "fcff":      fcff,
        "nopat":     nopat,
        "fvok_ham":  fvok_ham,
        "fvok":      fvok,
        "amort":     amort,
        "capex_ham": capex_ham,
        "capex_duz": capex_duz,
        "net_capex": net_capex,
        "delta_nwc": delta_nwc_f,
        "nwc_oran":  nwc_oran,
        "nwc_kaynak": nwc_kaynak,
        "ticari_borc": ticari_borc,

        # Ar-Ge
        "arge_var":       arge["var"],
        "arge_cari":      arge["arge_cari"],
        "arge_amort":     arge["amortizasyon"],
        "research_asset": arge["research_asset"],
        "arge_duzeltme":  arge["duzeltme"],

        # Terminal
        "term_roc":   term_roc,
        "term_reinv": term_reinv,
        "term_fcff":  term_fcff,
        "tv":         tv,

        # Değer
        "pv_fcff":   pv_fcff,
        "pv_tv":     pv_tv,
        "firma_deg": firma_deg,
        "oz_deg":    oz_deg,
        "proj":      pd.DataFrame(proj),

        # Uyarılar
        "fvok_uyari": fvok_kontrol,
        "puan":       _sf(row.get("Puan")),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PORTFÖY DAĞILIMI
# Damodaran AIMRIndia2013.pdf Slayt 39
# "Be diversified" — tek pozisyon max %15
# ─────────────────────────────────────────────────────────────────────────────

def portfoy_hesapla(giris_listesi: list, tutar: float) -> pd.DataFrame:
    if not giris_listesi:
        return pd.DataFrame()
    df = pd.DataFrame(giris_listesi)
    df = df[df["iskonto"] > 0].copy()
    if df.empty:
        return df
    toplam             = df["iskonto"].sum()
    df["Ham Ağırlık (%)"] = df["iskonto"] / toplam * 100
    df["Ağırlık (%)"]     = df["Ham Ağırlık (%)"].clip(upper=15)
    norm               = df["Ağırlık (%)"].sum()
    df["Ağırlık (%)"] = df["Ağırlık (%)"] / norm * 100
    df["Tutar (USD)"] = df["Ağırlık (%)"] / 100 * tutar
    return df.sort_values("Ağırlık (%)", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# SİNYAL GEÇİŞLERİ
# ─────────────────────────────────────────────────────────────────────────────

GECIS_TANIMLARI = {
    "GİRİŞ→ÇIKIŞ": {"etiket": "Çıkış Sinyali",  "oncelik": 0},
    "ÇIKIŞ→GİRİŞ": {"etiket": "Dönüş Fırsatı",  "oncelik": 1},
    "İZLE→GİRİŞ":  {"etiket": "Yeni Fırsat",     "oncelik": 2},
    "GİRİŞ→GİRİŞ": {"etiket": "Devam",           "oncelik": 3},
    "GİRİŞ→İZLE":  {"etiket": "Zayıflıyor",      "oncelik": 4},
    "ÇIKIŞ→İZLE":  {"etiket": "Toparlanıyor",    "oncelik": 5},
    "İZLE→ÇIKIŞ":  {"etiket": "Dikkat",          "oncelik": 6},
    "ÇIKIŞ→ÇIKIŞ": {"etiket": "Hâlâ Pahalı",    "oncelik": 7},
    "İZLE→İZLE":   {"etiket": "Nötr",            "oncelik": 8},
}
