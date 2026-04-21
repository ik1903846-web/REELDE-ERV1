# REELDEĞER — Damodaran DCF Sistemi

Türkiye (BIST) için USD bazlı Damodaran DCF yatırım analiz sistemi.

## Kurulum

```bash
pip install -r requirements.txt
streamlit run reeldeger_app.py
```

## Gerekli Dosyalar

### 1. Fastweb USD Excel (zorunlu)
Fastweb'den dönem bazlı export — şu kolonlar olmalı:

| Kolon | Açıklama |
|---|---|
| Kod | Hisse kodu |
| Puan | Fastweb puanı |
| Hisse Sektör | Sektör adı |
| Beta | Piyasa betası |
| Esas Faaliyet Karı /Zararı Net (Yıllık) | FVÖK (USD) |
| Amortismanlar (Yıllık) | USD |
| Yatırım Faaliyetlerinden Kaynaklanan Nakit Akışlar | CapEx (USD) |
| Finansal Borçlar | USD |
| Kısa Vadeli Borçlar | USD |
| Uzun Vadeli Borçlar | USD |
| Özkaynaklar | USD |
| Piyasa Değeri | USD |
| Nakit ve Nakit Benzerleri | USD |
| Dönen Varlıklar | USD |
| Aktifler | USD |
| Net Satışlar (Yıllık) | USD |
| Yurt İçi Satışlar | USD |
| Yurt Dışı Satışlar | USD |
| Finansman Gelirleri | USD |
| Finansman Giderleri | USD |
| Stoklar | USD — Slayt 89 NWC için |
| Ticari Alacaklar | USD — Slayt 89 NWC için |
| Hisse Kapanış | USD |

### 2. Fintables USD Excel (önerilen)
Fintables'tan export — Ar-Ge ve Ticari Borçlar için:

| Kolon | Açıklama |
|---|---|
| Şirket | Hisse kodu |
| Arge Giderleri (2025/12, USD) | Ar-Ge — 5 yıl |
| Arge Giderleri (2024/12, USD) | ... |
| Arge Giderleri (2023/12, USD) | ... |
| Arge Giderleri (2022/12, USD) | ... |
| Arge Giderleri (2021/12, USD) | ... |
| Ticari Borçlar (2025/12, USD) | NWC için |

## Damodaran Formülleri

| Formül | Slayt |
|---|---|
| FCFF = NOPAT − Net CapEx − ΔNWC | 66 |
| Ke = Rf + β×ERP + λ×CRP | 34 |
| λ = Firma yurtiçi% / Sektör ort% | 33 |
| Kd = Rf + TR Spread + Şirket Spread | 55 |
| Coverage = FVÖK / Finansman Giderleri → Rating | 53-54 |
| WACC = Market Value ağırlıkları | 57 |
| WACC Borcu = Finansal Borçlar (ticari borç hariç) | 57 |
| ROC = NOPAT / (Fin.Borç + Özkaynak + Research Asset) | 126, 78 |
| g = Reinv Rate × ROC | 116 |
| Terminal ROC = WACC | 142 |
| Terminal Reinv = g / WACC | 144 |
| NWC = (Stoklar + Ticari Alacaklar) − Ticari Borçlar | 89 |
| Ar-Ge Research Asset aktifleştirme (5 yıl) | 76-77 |
| Nakit = non-operating asset, ayrı eklenir | 153 |
| Negatif FVÖK → hesaplama dışı | 81 |

## Parametreler (Şubat 2026)

Sistem ctryprem.html'den otomatik günceller:
- Rf: %3.96
- ERP (Olgun Piyasa): %4.23
- Türkiye CRP: %4.66 (Ba3)
- TR Default Spread: %3.06
- Vergi: %25
- Terminal g: %2.50 (USD)

## Sınırlamalar

- Beta: Regression beta (bottom-up değil) — Slayt 47
- Kira: TFRS 16 zaten Finansal Borçlar içinde — ayrıca girilmez
- Satın alma normalizasyonu: Tek dönem veri — Slayt 86
- 2-Stage model kullanılıyor — Slayt 150

---
Kaynak: pages.stern.nyu.edu/~adamodar
