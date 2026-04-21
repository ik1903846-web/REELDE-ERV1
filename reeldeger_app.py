"""
REELDEĞER — Streamlit Uygulaması
Kaynak: pages.stern.nyu.edu/~adamodar
Kullanim: streamlit run reeldeger_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
def _excel_yukle(dosya) -> pd.DataFrame:
    """Excel yükle. Stil hatası reeldeger_dcf'deki patch ile giderildi."""
    return pd.read_excel(dosya)

from reeldeger_dcf import (
    dcf_hesapla, finansal_mi, portfoy_hesapla,
    fintables_yukle, sektor_ortalamalari_hesapla,
    PARAMETRELER, GECIS_TANIMLARI
)

st.set_page_config(
    page_title="REELDEĞER ▲",
    page_icon="▲",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .stApp { background-color: #07070f; color: #e4e4e7; }
  .block-container { padding-top: 1rem; }
  div[data-testid="metric-container"] {
      background: #18181b; border: 1px solid #27272a;
      border-radius: 10px; padding: 12px;
  }
  .karar-giris { background:#052e16; border:2px solid #16a34a;
                 border-radius:12px; padding:16px; }
  .karar-cikis { background:#2a0a0a; border:2px solid #dc2626;
                 border-radius:12px; padding:16px; }
  .karar-izle  { background:#1a1200; border:2px solid #d97706;
                 border-radius:12px; padding:16px; }
  .ref { font-size:11px; color:#52525b; border-left:2px solid #27272a;
         padding-left:8px; margin-top:6px; }
  .kira-box { background:#0f172a; border:1px solid #3b82f6;
              border-radius:8px; padding:12px; margin-top:8px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DAMODARAN OTOMATIK GUNCELLEME
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def damodaran_guncelle():
    try:
        r = requests.get(
            "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html",
            timeout=15, headers={"User-Agent": "Mozilla/5.0"}
        )
        soup = BeautifulSoup(r.text, "lxml")
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            if "Turkey" in cells[0].get_text():
                try:
                    adj_spread = float(cells[2].get_text(strip=True).replace("%", ""))
                    crp        = float(cells[3].get_text(strip=True).replace("%", ""))
                    erp        = float(cells[4].get_text(strip=True).replace("%", ""))
                    vergi      = float(cells[5].get_text(strip=True).replace("%", "")) / 100
                    return {**PARAMETRELER,
                            "tr_default_spread": adj_spread,
                            "crp": crp, "erp": erp, "vergi": vergi,
                            "tarih": f"Otomatik — {datetime.now().strftime('%d.%m.%Y')}",
                            "oto": True}
                except Exception:
                    pass
    except Exception:
        pass
    return {**PARAMETRELER, "tarih": "Varsayılan (Şubat 2026)", "oto": False}


# ─────────────────────────────────────────────────────────────────────────────
# YARDIMCI
# ─────────────────────────────────────────────────────────────────────────────
def fmt_usd(v, d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    a = abs(v)
    if a >= 1e9: return f"${v/1e9:.{d}f}B"
    if a >= 1e6: return f"${v/1e6:.{d}f}M"
    if a >= 1e3: return f"${v/1e3:.{d}f}K"
    return f"${v:.4f}"

def fmt_pct(v, d=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"%{v:.{d}f}"

def karar_ikon(k):
    return {"GİRİŞ": "🟢", "ÇIKIŞ": "🔴", "İZLE": "🟡"}.get(k, "⚪")


# ─────────────────────────────────────────────────────────────────────────────
# ANA UYGULAMA
# ─────────────────────────────────────────────────────────────────────────────
def main():

    # ── SIDEBAR ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ▲ REELDEĞER")
        st.caption("Damodaran DCF · USD · BIST")
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Güncelle", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with c2:
            st.caption("Ocak/Temmuz")

        D = damodaran_guncelle()
        st.caption(f"{'🟢 Otomatik' if D.get('oto') else '🟡 Varsayılan'}: {D.get('tarih','')}")

        with st.expander("Parametreler (ctryprem.html)", expanded=False):
            D["rf"]               = st.number_input("Rf (%)", value=D.get("rf", 3.96), step=0.01, format="%.2f")
            D["erp"]              = st.number_input("ERP Olgun P. (%)", value=D.get("erp", 4.23), step=0.01, format="%.2f")
            D["crp"]              = st.number_input("Türkiye CRP (%)", value=D.get("crp", 4.66), step=0.01, format="%.2f")
            D["tr_default_spread"]= st.number_input("TR Default Spread (%)", value=D.get("tr_default_spread", 3.06), step=0.01, format="%.2f")
            D["vergi"]            = st.number_input("Kurumlar Vergisi", value=D.get("vergi", 0.25), step=0.01, format="%.2f")
            D["stable_g"]         = st.number_input("Terminal Büyüme (%)", value=D.get("stable_g", 2.50), step=0.1, format="%.1f")
            st.caption("Terminal ROC = WACC (Damodaran Slayt 142)")

        st.divider()
        st.markdown("**Fastweb USD Excel**")
        fastweb_dosyalar = st.file_uploader(
            "Dönem dosyaları (çoklu)", type=["xlsx"], accept_multiple_files=True
        )
        st.markdown("**Fintables USD Excel** *(Ar-Ge + Ticari Borç)*")
        fintables_dosya = st.file_uploader(
            "Fintables USD dosyası", type=["xlsx"], accept_multiple_files=False,
            key="fintables"
        )
        fin_goster    = st.checkbox("Finansal şirketleri göster", value=False)
        portfoy_tutar = st.number_input("Portföy Tutarı (USD)", value=100_000, step=10_000)

    # ── YÜKLENMEDİYSE ────────────────────────────────────────────────────────
    if not fastweb_dosyalar:
        st.markdown("""
        ## ▲ REELDEĞER — Damodaran DCF Sistemi

        **Fastweb USD Excel yükleyin.**

        | # | Düzeltme | Kaynak |
        |---|---|---|
        | 1 | Kd = Synthetic Rating | Slayt 53-56 |
        | 2 | Terminal ROC = WACC | Slayt 142-144 |
        | 3 | Lambda = Sektör bazında | Slayt 33 |
        | 4 | ROC = Finansal Borç + Research Asset | Slayt 126, 78 |
        | 5 | FVÖK Normalize kontrolü | Slayt 79-80 |
        | 6 | Ar-Ge = Research Asset aktifleştirme | Slayt 76-77 |
        | 7 | NWC = Ticari Borçlar (non-debt CL) | Slayt 89 |
        | 8 | Kira Borcu = WACC borcuna eklenir | Slayt 72-74 |

        *Kaynak: pages.stern.nyu.edu/~adamodar*
        """)
        return

    # ── DOSYALARI OKU ─────────────────────────────────────────────────────────
    donemler = {}
    for f in sorted(fastweb_dosyalar, key=lambda x: x.name):
        try:
            donemler[f.name] = _excel_yukle(f)
        except Exception as e:
            st.error(f"{f.name}: {e}")

    if not donemler:
        return

    # Fintables
    ft_data = {}
    if fintables_dosya:
        ft_data = fintables_yukle(fintables_dosya)
        st.sidebar.success(f"✅ Fintables: {len(ft_data)} şirket yüklendi")
    else:
        st.sidebar.info("ℹ Fintables yüklenmedi — Ar-Ge ve Ticari Borç kullanılmayacak")

    # Son dönem
    son_ad = sorted(donemler.keys())[-1]
    son_df = donemler[son_ad]

    # Sektör ortalamaları
    tum_df = pd.concat(list(donemler.values()), ignore_index=True)
    sektor_ort = sektor_ortalamalari_hesapla(tum_df)
    D["sektor_ort"] = sektor_ort
    bist_ort = sektor_ort.get("__BIST__", 0.546)

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Şirket Analizi", "🔄 Sinyal Takip", "💼 Portföy", "📋 Parametreler", "📚 Kaynaklar"
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1 — ŞİRKET ANALİZİ
    # ═════════════════════════════════════════════════════════════════════════
    with tab1:
        col_l, col_r = st.columns([1, 3])

        with col_l:
            kodlar = []
            for _, row in son_df.iterrows():
                if not fin_goster and finansal_mi(row):
                    continue
                if row.get("Kod"):
                    kodlar.append(row["Kod"])

            secilen = st.selectbox("Şirket", kodlar, label_visibility="collapsed")

            # Özet istatistikler
            tum_r = [dcf_hesapla(r, D, ft_data.get(str(r.get("Kod", "")), {}))
                     for _, r in son_df.iterrows()
                     if not finansal_mi(r) and r.get("Kod")]
            tum_r = [x for x in tum_r if x and "hata" not in x]

            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 GİRİŞ", sum(1 for x in tum_r if x["karar"] == "GİRİŞ"))
            c2.metric("🟡 İZLE",  sum(1 for x in tum_r if x["karar"] == "İZLE"))
            c3.metric("🔴 ÇIKIŞ", sum(1 for x in tum_r if x["karar"] == "ÇIKIŞ"))

        # Seçilen şirket
        rows = son_df[son_df["Kod"] == secilen]
        if rows.empty:
            col_r.warning("Şirket bulunamadı")
            return

        row = rows.iloc[0]

        if finansal_mi(row):
            col_r.error("⚠ Finansal şirket — FCFF uygulanamaz (Damodaran spreadsh.htm)")
            return

        # ── TFRS 16 NOTU ─────────────────────────────────────────────────────
        with col_l:
            st.markdown("---")
            st.info(
                "**TFRS 16 — Kira Yükümlülükleri**\n\n"
                "BIST şirketleri 2019'dan itibaren TFRS 16 uygular. "
                "Kira yükümlülükleri **Finansal Borçlar** içinde yer alır. "
                "Ayrıca girilmesine gerek yoktur — çifte sayma olur."
            )

        # DCF
        ft_row = ft_data.get(secilen, {})
        sonuc  = dcf_hesapla(row, D, ft_row)

        if "hata" in sonuc:
            col_r.error(f"WACC ({fmt_pct(sonuc.get('wacc', 0))}) terminal büyümeden düşük.")
            return

        # Karar kartı
        with col_r:
            k = sonuc["karar"]
            st.markdown(f"""
            <div class="karar-{'giris' if k=='GİRİŞ' else 'cikis' if k=='ÇIKIŞ' else 'izle'}">
            <h2>{karar_ikon(k)} {secilen} — {k}</h2>
            <p>İçsel: <b>{fmt_usd(sonuc['icsel'], 3)}</b> &nbsp;·&nbsp; 
               Piyasa: <b>{fmt_usd(sonuc['fiyat'], 3)}</b>
               {'&nbsp;·&nbsp; İskonto: <b>' + fmt_pct(sonuc['iskonto']) + '</b>' if sonuc['iskonto'] else ''}
            </p>
            </div>
            """, unsafe_allow_html=True)

            if sonuc["fvok_uyari"]["uyari"]:
                st.warning(sonuc["fvok_uyari"]["mesaj"])

            if sonuc["arge_var"]:
                st.info(
                    f"🔬 Ar-Ge aktifleştirildi (Slayt 76-77): "
                    f"Cari={fmt_usd(sonuc['arge_cari'])} · "
                    f"Research Asset={fmt_usd(sonuc['research_asset'])} · "
                    f"FVÖK düzeltme={fmt_usd(sonuc['arge_duzeltme'])}"
                )

            if sonuc["nwc_kaynak"] == "ticari_borc":
                st.success(f"✅ NWC: Ticari Borçlar ({fmt_usd(sonuc['ticari_borc'])}) — Slayt 89")
            elif ft_data:
                st.info("ℹ NWC: Bu şirket için Ticari Borç = 0 — KV Borç kullanılıyor")
            else:
                st.warning("⚠ NWC: Fintables yüklenmedi — KV Borç kullanılıyor")

        # Metrikler
        m = st.columns(6)
        m[0].metric("İçsel/Hisse",  fmt_usd(sonuc["icsel"], 3))
        m[1].metric("Piyasa",       fmt_usd(sonuc["fiyat"], 3))
        m[2].metric("WACC",         fmt_pct(sonuc["wacc"]))
        m[3].metric("Ke",           fmt_pct(sonuc["ke"]))
        m[4].metric("Kd (pretax)",  fmt_pct(sonuc["kd_pretax"]))
        m[5].metric("λ (Lambda)",   f"{sonuc['lam']:.2f}")

        st.divider()
        c_dcf, c_girdi = st.columns(2)

        with c_dcf:
            st.markdown("**DCF Sonuçları**")
            items = {
                "FVÖK (ham)":         fmt_usd(sonuc["fvok_ham"]),
                "FVÖK (Ar-Ge düz.)":  fmt_usd(sonuc["fvok"]),
                "NOPAT":              fmt_usd(sonuc["nopat"]),
                "FCFF (Baz)":         fmt_usd(sonuc["fcff"]),
                "PV (5Y FCFF)":       fmt_usd(sonuc["pv_fcff"]),
                "Terminal FCFF":      fmt_usd(sonuc["term_fcff"]),
                "PV (Terminal)":      fmt_usd(sonuc["pv_tv"]),
                "+ Nakit":            fmt_usd(row.get("Nakit ve Nakit Benzerleri", 0)),
                "Firma Değeri":       fmt_usd(sonuc["firma_deg"]),
                "- Borç (toplam)":    fmt_usd(sonuc["top_borc"]),
                "  KV+UV Borç":       fmt_usd(row.get("Kısa Vadeli Borçlar", 0) + row.get("Uzun Vadeli Borçlar", 0)),
                "  (TFRS 16 dahil)":  "Finansal Borç içinde",
                "Özsermaye Değeri":   fmt_usd(sonuc["oz_deg"]),
                "İçsel/Hisse":        fmt_usd(sonuc["icsel"], 3),
            }
            for k2, v in items.items():
                indent = "&nbsp;&nbsp;" if k2.startswith("  ") else ""
                st.markdown(f"{indent}`{k2.strip()}`: **{v}**", unsafe_allow_html=True)

            st.markdown("""<div class="ref">
            FCFF: Slayt 66 | Terminal ROC=WACC: Slayt 142-144<br>
            Nakit ayrı: Slayt 153 | Kira borç: Slayt 72-74
            </div>""", unsafe_allow_html=True)

        with c_girdi:
            st.markdown("**Ke, Kd & Büyüme**")

            st.markdown("*Ke = Rf + β×ERP + λ×CRP (Slayt 34)*")
            ke_d = {
                "Rf":                f"%{D['rf']}",
                "Beta (β)":          f"{sonuc['beta']:.3f}",
                "ERP (Olgun P.)":    f"%{D['erp']}",
                "λ (değer)":         f"{sonuc['lam']:.2f}",
                "λ (kaynak)":        sonuc.get("lam_kaynak", "—"),
                "λ (sektör ort.)":   f"%{sonuc.get('lam_payda', 0)*100:.1f}",
                "CRP":               f"%{D['crp']}",
                "Ke":                fmt_pct(sonuc["ke"]),
            }
            for k2, v in ke_d.items():
                st.markdown(f"`{k2}`: **{v}**")

            st.markdown("---")
            st.markdown("*Kd Synthetic Rating (Slayt 53-56)*")
            kd_d = {
                "Faiz Karş. Oranı":   f"{sonuc['coverage']:.2f}x",
                "Şirket Spread":       f"%{sonuc['sirket_spread']:.2f}",
                "TR Spread":           f"%{D['tr_default_spread']}",
                "Kd (pretax)":         fmt_pct(sonuc["kd_pretax"]),
                "Kd (vergi sonrası)":  fmt_pct(sonuc["kd_aftertax"]),
            }
            for k2, v in kd_d.items():
                st.markdown(f"`{k2}`: **{v}**")

            st.markdown("---")
            st.markdown("*g = ROC × Reinv Rate (Slayt 116)*")
            g_d = {
                "ROC (Fin.Borç + R.Asset)": fmt_pct(sonuc["roc"] * 100),
                "Research Asset":            fmt_usd(sonuc["research_asset"]),
                "Reinv Rate":                fmt_pct(sonuc["reinv_rate"] * 100),
                "CapEx (Ar-Ge dahil)":       fmt_usd(sonuc["capex_duz"]),
                "g (Fundamental)":           fmt_pct(sonuc["g_fund"] * 100),
                "g (Kullanılan)":            fmt_pct(sonuc["buyume"] * 100, 0),
                "Terminal ROC = WACC":       fmt_pct(sonuc["term_roc"] * 100),
                "Terminal Reinv":            fmt_pct(sonuc["term_reinv"] * 100),
            }
            for k2, v in g_d.items():
                st.markdown(f"`{k2}`: **{v}**")

        # Projeksiyon grafiği
        st.divider()
        proj = sonuc["proj"]
        fig = go.Figure()
        fig.add_bar(x=proj["Yıl"].astype(str), y=proj["FCFF"],
                    name="FCFF", marker_color="#3b82f6")
        fig.add_bar(x=proj["Yıl"].astype(str), y=proj["PV"],
                    name="PV(FCFF)", marker_color="#22c55e")
        fig.update_layout(
            title="FCFF Projeksiyonu (USD · 2-Stage)",
            paper_bgcolor="#07070f", plot_bgcolor="#07070f",
            font_color="#e4e4e7", barmode="group", height=280,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2 — SİNYAL TAKİP
    # ═════════════════════════════════════════════════════════════════════════
    with tab2:
        if len(donemler) < 2:
            st.info("En az 2 dönem yükleyin.")
        else:
            sirali   = sorted(donemler.keys())
            eski_ad  = sirali[-2]
            yeni_ad  = sirali[-1]
            st.markdown(f"**{eski_ad}** → **{yeni_ad}**")

            @st.cache_data(ttl=3600)
            def gecis_hesapla(_D_hash, eski_a, yeni_a):
                gecisler = []
                for _, yr in donemler[yeni_a].iterrows():
                    kod = yr.get("Kod")
                    if not kod or finansal_mi(yr):
                        continue
                    eski_satirlar = donemler[eski_a][donemler[eski_a]["Kod"] == kod]
                    if eski_satirlar.empty:
                        continue
                    ftr = ft_data.get(str(kod), {})
                    er  = dcf_hesapla(eski_satirlar.iloc[0], D, ftr)
                    yr2 = dcf_hesapla(yr, D, ftr)
                    if not er or not yr2 or "hata" in er or "hata" in yr2:
                        continue
                    key = f"{er['karar']}→{yr2['karar']}"
                    g   = GECIS_TANIMLARI.get(key)
                    if not g:
                        continue
                    gecisler.append({
                        "Kod": kod, "Geçiş": key, "Etiket": g["etiket"],
                        "Öncelik": g["oncelik"],
                        "Eski K": er["karar"], "Yeni K": yr2["karar"],
                        "Eski İsk": round(er["iskonto"], 1) if er["iskonto"] else None,
                        "Yeni İsk": round(yr2["iskonto"], 1) if yr2["iskonto"] else None,
                        "Fiyat": fmt_usd(yr.get("Hisse Kapanış"), 3),
                        "Puan": f"{yr.get('Puan', 0):.0f}",
                    })
                return gecisler

            gecisler = gecis_hesapla(
                hash(str(D.get("rf")) + str(D.get("crp"))),
                eski_ad, yeni_ad
            )

            if gecisler:
                gdf = pd.DataFrame(gecisler).sort_values("Öncelik")
                cc  = st.columns(4)
                cc[0].metric("Çıkış (G→Ç)", len(gdf[gdf["Geçiş"] == "GİRİŞ→ÇIKIŞ"]))
                cc[1].metric("Yeni Fırsat", len(gdf[gdf["Geçiş"] == "İZLE→GİRİŞ"]))
                cc[2].metric("Devam (G→G)", len(gdf[gdf["Geçiş"] == "GİRİŞ→GİRİŞ"]))
                cc[3].metric("Toplam Değişim", len(gdf[gdf["Eski K"] != gdf["Yeni K"]]))

                filtre = st.multiselect("Geçiş tipi",
                    gdf["Geçiş"].unique().tolist(),
                    default=gdf["Geçiş"].unique().tolist())
                st.dataframe(
                    gdf[gdf["Geçiş"].isin(filtre)]
                    [["Kod","Etiket","Eski K","Yeni K","Eski İsk","Yeni İsk","Fiyat","Puan"]],
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Sinyal geçişi bulunamadı.")

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 3 — PORTFÖY
    # ═════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("""
        **Damodaran Portföy Kuralları** *(AIMRIndia2013.pdf Slayt 39)*
        > *"Be diversified"* · *"Have a long time horizon"*
        """)

        giris_listesi = []
        for _, row2 in son_df.iterrows():
            if finansal_mi(row2):
                continue
            kod2 = str(row2.get("Kod", ""))
            r2   = dcf_hesapla(row2, D, ft_data.get(kod2, {}))
            if r2 and r2.get("karar") == "GİRİŞ" and r2.get("iskonto"):
                giris_listesi.append({
                    "kod": kod2, "iskonto": r2["iskonto"],
                    "icsel": r2["icsel"], "fiyat": r2["fiyat"],
                    "wacc": r2["wacc"], "lam": r2["lam"],
                })

        port = portfoy_hesapla(giris_listesi, portfoy_tutar)
        if port.empty:
            st.info("GİRİŞ sinyali yok.")
        else:
            cc = st.columns(3)
            cc[0].metric("GİRİŞ Hisse", len(port))
            cc[1].metric("Ort. İskonto", fmt_pct(port["iskonto"].mean()))
            cc[2].metric("Portföy", f"${portfoy_tutar:,.0f}")

            gdf2 = port[["kod","iskonto","icsel","Ağırlık (%)","Tutar (USD)"]].copy()
            gdf2.columns = ["Kod","İskonto(%)","İçsel($)","Ağırlık(%)","Tutar(USD)"]
            gdf2["İskonto(%)"] = gdf2["İskonto(%)"].apply(lambda x: f"%{x:.1f}")
            gdf2["İçsel($)"]   = gdf2["İçsel($)"].apply(lambda x: fmt_usd(x, 3))
            gdf2["Ağırlık(%)"] = gdf2["Ağırlık(%)"].apply(lambda x: f"%{x:.1f}")
            gdf2["Tutar(USD)"] = gdf2["Tutar(USD)"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(gdf2, use_container_width=True, hide_index=True)

            fig = px.pie(port, names="kod", values="Ağırlık (%)", title="Portföy Dağılımı")
            fig.update_layout(paper_bgcolor="#07070f", font_color="#e4e4e7", height=320)
            st.plotly_chart(fig, use_container_width=True)
            st.warning("⚠ Tek pozisyon max %15 · Yatırım tavsiyesi değildir")

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 4 — PARAMETRELER
    # ═════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## Sistem Parametreleri — Damodaran Kaynakları")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Piyasa Parametreleri**")
            st.markdown(f"""
| Parametre | Değer | Kaynak |
|---|---|---|
| Rf | %{D['rf']} | ctryprem.html |
| ERP (Olgun P.) | %{D['erp']} | ctryprem.html |
| Türkiye CRP | %{D['crp']} | ctryprem.html Ba3 |
| TR Default Spread | %{D['tr_default_spread']} | ctryprem.html |
| Kurumlar Vergisi | %{D['vergi']*100:.0f} | ctryprem.html |
| Terminal Büyüme | %{D['stable_g']} | USD nominal |
| Ar-Ge Ömrü | 5 yıl | Damodaran Slayt 76 |
""")

        with c2:
            st.markdown("**Formüller**")
            st.markdown("""
| Bileşen | Formül | Slayt |
|---|---|---|
| FCFF | NOPAT + Amort − CapEx(Ar-Ge dahil) − ΔNWC | 66, 86 |
| Ke | Rf + β×ERP + λ×CRP | 34 |
| λ | Yurtiçi% / Sektör ort% | 33 |
| Kd | Rf + TR Sp. + Şirket Sp. | 55 |
| Coverage | FVÖK(düz.) / Fin.Gider | 53-54 |
| WACC | Market value ağırlıkları | 57 |
| ROC | NOPAT / (Fin.Borç + Özkaynak + R.Asset) | 126, 78 |
| g | ROC × Reinv Rate | 116 |
| Terminal Reinv | g / WACC | 144 |
| NWC | Non-cash CA − Ticari Borçlar | 89 |
| Ar-Ge | Research Asset aktifleştirme | 76-77 |
| Kira | KV+UV kira borcu borca eklenir | 72-74 |
| + Nakit | Non-operating asset, ayrı eklenir | 153 |
""")

        st.markdown("---")
        st.markdown("**Sektör Lambda Ortalamaları (Hesaplanan)**")
        sektor_tablo = {k: f"%{v*100:.1f}"
                        for k, v in sektor_ort.items() if k != "__BIST__"}
        sektor_tablo["── BIST Genel Ortalama"] = f"%{bist_ort*100:.1f}"
        st.dataframe(
            pd.DataFrame(list(sektor_tablo.items()), columns=["Sektör", "Ort. Yurtiçi Oranı"]),
            use_container_width=True, hide_index=True
        )

        st.markdown("---")
        st.markdown("""
**Sınırlamalar**
- **Kira yükümlülüğü:** TFRS 16 kapsamında zaten Finansal Borçlar içinde — ayrıca girilmez
- **Türkiye piyasa ort. yurtiçi oranı (%54.6):** Yüklenen Excel'deki BIST şirketlerinden hesaplandı
- **Dönem kullanım mantığı:**
  - **DCF hesaplama & Portföy:** En son yüklenen dönemin verisi (örn. 202512)
  - **Sinyal Takip:** Son 2 dönem karşılaştırılır (örn. 202509 → 202512)
  - **Sektör Lambda ortalamaları:** Tüm yüklenen dönemler birleştirilerek hesaplanır (daha geniş veri tabanı)
  - **TTM (Trailing 12-month):** Son 4 çeyreğin kazancı toplanarak en güncel 12 aylık FVÖK elde edilir — şu an her dönemin kendi yıllık verisi kullanılıyor, TTM desteği eklenecek
- **Beta:** Regression beta (bottom-up değil) — Slayt 47
- **Satın alma normalizasyonu:** Tek dönem CapEx — Slayt 86

*Kaynak: pages.stern.nyu.edu/~adamodar · dcfallOld.pdf · ctryprem.html*
""")




    # ═════════════════════════════════════════════════════════════════════════
    # TAB 5 — KAYNAKLAR
    # ═════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("## 📚 Veri Kaynakları ve Referanslar")
        st.divider()

        # ── DAMODARAN BİRİNCİL KAYNAKLAR ─────────────────────────────────────
        st.markdown("### 1. Damodaran Birincil Kaynakları")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("""
**DCF Formülleri — Ana PDF**
`pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/dcfallOld.pdf`

| Formül | Slayt |
|---|---|
| FCFF = NOPAT − Net CapEx − ΔNWC | 66 |
| Ke = Rf + β×ERP + λ×CRP | 34 |
| λ = Firma yurtiçi% / Sektör ort% | 33 |
| Coverage → Synthetic Rating → Kd | 53-54 |
| Kd = Rf + Ülke Spread + Şirket Spread | 55 |
| WACC = Market value ağırlıkları | 57 |
| WACC borcu = Finansal borç (ticari borç hariç) | 57 |
| ROC = NOPAT / (Fin.Borç + Özkaynak + R.Asset) | 126, 78 |
| g = Reinv Rate × ROC | 116 |
| Reinv Rate = (Net CapEx + ΔNWC) / NOPAT | 126 |
| Terminal ROC = WACC (excess return = 0) | 142 |
| Terminal Reinv = g / WACC | 144 |
| NWC = (Stoklar + Ticari Alacaklar) − Ticari Borçlar | 89 |
| NWC negatifse sıfır al | 91 |
| Ar-Ge Research Asset aktifleştirme (5 yıl) | 76-77 |
| Adj. Net CapEx = Net CapEx + Ar-Ge − Amort_Ar-Ge | 86 |
| Nakit = non-operating asset, ayrı eklenir | 153 |
| Negatif FVÖK → normalize edilmeden değerleme yapılamaz | 81 |
| Vergi = marjinal oran | 83 |
| Büyüme alt sınırı yok (negatif olabilir) | 139 |
""")

        with c2:
            st.markdown("""
**Ülke Risk Primleri — Güncel Tablo**
`pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html`

Güncelleme: Ocak + Temmuz (yılda 2 kez)
Sistem otomatik çeker — sidebar'da "🔄 Güncelle" butonu

| Parametre | Değer | Nereden |
|---|---|---|
| Rf | %3.96 | ABD T-Bond − US default spread |
| ERP (Olgun) | %4.23 | Implied ERP — S&P 500 |
| Türkiye CRP | %4.66 | Ba3 rating — adjusted spread |
| TR Default Spread | %3.06 | Ba3 sovereign CDS / bond |
| Kurumlar Vergisi | %25 | ctryprem tablosu — Türkiye |
| Terminal g | %2.50 | USD nominal — ABD uzun vadeli |

---

**Lambda (λ) Payda — Türkiye Piyasa Ortalaması**
`Fastweb verisi — 472 BIST şirketi`

Slayt 33: *"% revenues domestically — average firm"*
Sistem bunu otomatik hesaplar:
- Her sektörün yurtiçi satış oranı ortalaması
- En az 5 şirketi olan sektörler için sektör bazında
- Diğerleri için BIST genel ortalaması (%54.6)
""")

        st.divider()

        # ── VERİ KAYNAKLARI ───────────────────────────────────────────────────
        st.markdown("### 2. Fastweb — Ana Finansal Veri")
        st.markdown("""
**URL:** `fastweb.com.tr` → Tarayıcı → Export → USD seçili

**Hangi veriler alınır:**

| Kolon | Kullanım | Damodaran Slayt |
|---|---|---|
| Esas Faaliyet Karı (Yıllık) | FVÖK → NOPAT | 66 |
| Amortismanlar (Yıllık) | Net CapEx hesabı | 66 |
| Yatırım Nakit Akışları | CapEx | 66, 85 |
| Finansal Borçlar | WACC borcu, ROC paydası | 57, 126 |
| Özkaynaklar | ROC paydası | 126 |
| Piyasa Değeri | WACC ağırlığı | 57 |
| Nakit | Non-op asset, ayrı eklenir | 153 |
| Dönen Varlıklar | NWC yedek hesabı | 89 |
| **Stoklar** | **NWC hesabı (Slayt 89)** | **89** |
| **Ticari Alacaklar** | **NWC hesabı (Slayt 89)** | **89** |
| Net Satışlar (Yıllık) | NWC/Satış oranı, Lambda | 89-91 |
| **Yurt İçi Satışlar** | **Lambda (λ) hesabı** | **33** |
| Yurt Dışı Satışlar | Lambda doğrulaması | 33 |
| Finansman Gelirleri | Normalize kontrol | 79-80 |
| Finansman Giderleri | Coverage → Kd | 53 |
| Beta | Ke hesabı | 34 |
| Hisse Sektör | Sektör lambda ortalaması | 33 |
| Hisse Kapanış | Hisse başına değer | — |
| Kısa Vadeli Borçlar | NWC yedek | 89 |
| Uzun Vadeli Borçlar | Bilgi | — |
| Aktifler | Finansal şirket tespiti | — |
""")

        st.divider()

        st.markdown("### 3. Fintables — Ar-Ge ve Ticari Borç")
        st.markdown("""
**URL:** `fintables.com` → Hisse Listesi → Export → USD seçili

**Neden gerekli:**
Fastweb'de Ar-Ge Giderleri ve Ticari Borçlar ayrı kolon olarak yok.

| Kolon | Kullanım | Damodaran Slayt |
|---|---|---|
| Arge Giderleri (2025/12, USD) | Research Asset hesabı — t | 76-77 |
| Arge Giderleri (2024/12, USD) | Research Asset — t-1 | 76-77 |
| Arge Giderleri (2023/12, USD) | Research Asset — t-2 | 76-77 |
| Arge Giderleri (2022/12, USD) | Research Asset — t-3 | 76-77 |
| Arge Giderleri (2021/12, USD) | Research Asset — t-4 | 76-77 |
| **Ticari Borçlar (2025/12, USD)** | **NWC non-debt CL** | **89** |

**Dönüşüm:** Fintables dönem sonu kuru ile USD'ye çevirir (~42.7 TRY/USD Aralık 2025)

**Ar-Ge Aktifleştirme (Slayt 76-77):**
```
Research Asset = Ar-Ge[t]×1.0 + Ar-Ge[t-1]×0.8 + Ar-Ge[t-2]×0.6
              + Ar-Ge[t-3]×0.4 + Ar-Ge[t-4]×0.2
Amortisman = (Ar-Ge[t-1] + t-2 + t-3 + t-4) / 5
Düzeltme FVÖK = Ar-Ge[t] − Amortisman
```
Cisco örneğiyle doğrulandı: Research Asset = 3,035 ✓
""")

        st.divider()

        # ── KABUL EDİLMİŞ SINIRLAMALAR ────────────────────────────────────────
        st.markdown("### 4. Kabul Edilmiş Sınırlamalar")
        st.markdown("""
| Konu | Damodaran Önerisi | Bizim Yaklaşımımız | Slayt |
|---|---|---|---|
| Beta | Bottom-up (sektör ort.) | Regression beta (Fastweb) | 47 |
| Satın alma | Normalize edilmiş ortalama | Tek yıl CapEx içinde | 86 |
| NOL carryforward | İlk yıllarda vergi = 0 | Sabit %25 marjinal | 84 |
| Model | Şirket büyüklüğüne göre 2 veya 3 stage | 2-stage tüm şirketler | 150 |
| Nakit beta düzeltmesi | β_op = β × (1 + Nakit/FD) | Raporlanan beta | 153 |
| Kira yükümlülüğü | Borç olarak ekle, FVÖK'ü düzelt | TFRS 16 zaten Finansal Borçlar içinde — ayrıca girilmez | 72-74 |
| Trailing 12-month | Son 4 çeyreği toplayıp tek kazanç | Yıllık dönem kullanılıyor (çeyreklik export gerekir) | 69 |
""")

        st.divider()

        st.markdown("### 5. Sistem Mimarisi")
        st.markdown("""
```
reeldeger_dcf.py   — DCF hesap motoru (tüm Damodaran formülleri)
reeldeger_app.py   — Streamlit arayüzü (bu dosya)
requirements.txt   — Python bağımlılıkları
```

**Veri akışı:**
```
Fastweb Excel (USD, dönemsel)
       ↓
Fintables Excel (USD, Ar-Ge + Ticari Borç)
       ↓
ctryprem.html (Damodaran — otomatik)
       ↓
reeldeger_dcf.py → DCF hesabı
       ↓
GİRİŞ / İZLE / ÇIKIŞ sinyali
```

**Kaynak:**
`pages.stern.nyu.edu/~adamodar`
`pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/dcfallOld.pdf`
`pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/ctryprem.html`
""")



if __name__ == "__main__":
    main()
