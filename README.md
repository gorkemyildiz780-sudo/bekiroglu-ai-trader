# BEKİROĞLU AI TRADER 2.0 — iPhone kurulumu

**Sadece sanal para.** Borsa API anahtarı, gerçek alım-satım, kaldıraç veya para çekme yetkisi içermez. Bu bir **kural tabanlı** alım-satım denemesidir, henüz LLM tabanlı bir AI ajanı değildir.

## Nasıl çalışır?

- GitHub Actions, yaklaşık her 30 dakikada bir (kesin zaman garantisi olmadan) `engine.py` dosyasını çalıştırır.
- Yahoo Finance üzerinden 6 aylık **günlük** fiyat verisi alınır.
- EMA20, EMA50, RSI14 koşullarıyla sanal AL/SAT kararı verilir.
- Sanal işlemler Supabase Postgres'teki tek bir JSONB kayıt içinde kalıcı saklanır.
- Streamlit uygulaması veriyi **sadece okur**. Gerçek işlem yapamaz.
- ABD hisseleri ve USD bazlı kripto sanal işlemlere açıktır. Döviz çiftleri sadece izlenir.
- Her işlemde yaklaşık %0,5 risk bütçesi, pozisyon başına en fazla %25, aynı anda en fazla 3 pozisyon, günlük %1,5 ve haftalık %3 yeni alım durdurma limiti, toplam %8 düşüşte kalıcı risk kilidi vardır. Bunlar garantili zarar sınırları değildir.
- **Önemli:** Sanal stop, veri taramasındaki fiyat üzerinden uygulanır. Stop fiyatından kesin gerçekleşme veya gün içi koruma yoktur.
- Komisyon, vergi, slippage ve spread modellemesi **henüz yoktur**; bu yüzden raporlanan sonuçlar gerçekçi kârlılığı olduğundan iyi gösterebilir.

## iPhone ile kurulum — sırasıyla

### 1) GitHub dosyalarını güncelle

Mevcut `gorkemyildiz780-sudo/bekiroglu-ai-trader` deposunu kullan. Bu ZIP'i iPhone **Dosyalar** uygulamasında aç. ZIP içinde `bekiroglu_ai_trader_2` klasörüne gir. **GitHub'a ZIP'i değil, içindeki dosyaları yükle.**

Ana dizine şu dosyaları yükle veya eskilerini değiştir:
- `app.py`
- `engine.py`
- `store.py`
- `requirements.txt`
- `README.md`
- `schema.sql`

Ayrıca GitHub deposunda `.github/workflows/paper-trader.yml` yolunda bir workflow oluşturulmalı. iPhone Safari'de depoda **Add file > Create new file** seçip dosya adına `.github/workflows/paper-trader.yml` yaz; ZIP'teki aynı dosyanın içeriğini kopyala, ardından **Commit changes**. (Klasör iç içe yükleme mümkünse dosyayı doğrudan doğru yola da yükleyebilirsin.)

### 2) Supabase veritabanı

1. Safari'de https://supabase.com/dashboard aç, ücretsiz hesap oluştur.
2. **New project** ile bir proje oluştur. Database password belirle ve güvenli sakla.
3. **SQL Editor > New query** bölümünde `schema.sql` dosyasındaki SQL'i yapıştır ve **Run** yap.
4. **Project Settings > API** (arayüz sürümüne göre **API Keys**) bölümünden **Project URL** ve **service_role / secret** anahtarını al.
5. **service_role / secret** anahtarını asla GitHub dosyalarına, README'ye, ekran görüntüsüne veya sohbet mesajına koyma. Bu anahtar veritabanında geniş yetkiye sahiptir.

### 3) GitHub Actions Secrets

Depo > **Settings > Secrets and variables > Actions > New repository secret**:
- `SUPABASE_URL` = Project URL
- `SUPABASE_KEY` = Supabase secret key (sb_secret_...) veya legacy service_role key

GitHub'da **Actions** sekmesinde **Paper trader (NO REAL MONEY)** iş akışını seç, **Run workflow** ile ilk kez çalıştır. İş akışı yeşil olmalı. Hata olursa Actions günlüklerine bak.

### 4) Streamlit secrets ve yeniden yayınlama

Streamlit Community Cloud'da mevcut uygulamayı aç > **Manage app** > **Settings > Secrets** (arayüz değişebilir). Şu biçimde gir:

```toml
SUPABASE_URL = "https://PROJE-ADIN.supabase.co"
SUPABASE_KEY = "SUPABASE_GIZLI_ANAHTARIN"
DASHBOARD_PASSWORD = "UZUN_BENZERSIZ_BIR_SIFRE"
```

Bu değerleri yalnızca Streamlit **Secrets** ekranına yaz, GitHub'a koyma. Uygulamayı yeniden başlat. Açılan panel şifre soracak.

### 5) Kontrol et

- GitHub Actions > son iş akışı **yeşil**.
- Streamlit'te şifreyi girince toplam sanal bakiye **$1.000** civarında görünür.
- Son tarama zamanı, sinyaller ve sanal işlemler görünür.
- Uygulamayı kapatıp yeniden açınca kayıtlar durur (Supabase çalıştığı sürece).

## Sınırlamalar ve güvenlik

- GitHub Actions cron **tam 7/24 kesintisiz sunucu değildir**: iş akışları gecikebilir veya atlanabilir. Yoğunluk, hizmet kesintisi ve repo hareketsizliği otomasyonu etkileyebilir. GitHub ücretsiz kullanım limitleri değişebilir.
- Supabase ücretsiz projeleri duraklatılabilir ve kullanım limitleri vardır. Ücretsiz planda süreklilik garantisi yoktur.
- Streamlit uygulaması internete açık olsa da panel parolası konulmuştur. Daha güçlü kimlik doğrulama için sonraki sürümde kullanıcı hesabı gerekir.
- Tek bir GitHub Actions workflow'unun çalışması `concurrency` ile seri hale getirilir. Streamlit veritabanına yazmaz.
- Fiyatlar gecikmeli olabilir; piyasa kapalıyken aynı kapanış fiyatı tekrar görülebilir.
- `schema.sql` RLS açar ve herkese açık okuma/yazma politikası tanımlamaz.
- Bu ilk sürümde haber analizi, LLM, backtest, işlem ücretleri ve gerçek zamanlı stoplar yoktur.
- Risk kilidi manuel sıfırlama gerektirir. Yanlışlıkla canlıya geçmeyi önlemek için hiçbir broker bağlantısı yoktur.

## Sonraki geliştirmeler

1. Gerçekçi spread/komisyon/slippage, işlem saatleri, borsa takvimi.
2. Ayrı backtest ve forward-test ölçüm raporu.
3. Telegram bildirimleri, servis sağlığı alarmı.
4. AI haber analizi (yalnızca yardımcı sinyal, emir yetkisi yok).
5. Kesintisiz çalışması gereken sistem için ücretli worker/VPS ve düzenli yedekleme.


## ÖNEMLİ: Önceki SQL ile uyum
Daha önce `trader_portfolio`, `trader_positions`, `trader_trades` tablolarını oluşturduysan **silme**. 2.0 motoru ayrı `trader_state` tablosunu kullanır. Supabase SQL Editor içinde `schema.sql` içeriğini **bir kez daha çalıştır**.

## Güvenli geçiş
İlk önce `engine.py`, `store.py`, `schema.sql` ve `.github/workflows/paper-trader.yml` dosyalarını ekle; eski `app.py` ve `requirements.txt` dosyalarını hemen değiştirme. Otomasyon yeşil çalışınca Streamlit uygulamasını yükselt. `requirements.txt` dosyasını Actions çalıştırılmadan önce güncellemek gerekir; bu eski Streamlit uygulamasının bağımlılıklarını değiştirebilir.
