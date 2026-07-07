# Youtube Music Desktop Player & Downloader

Modern, hızlı ve açık kaynaklı bir YouTube Music Masaüstü Oynatıcısı ve İndiricisi. PyQt6 kullanılarak geliştirilmiştir.

## Özellikler

* **Tam Kütüphane Erişimi:** YouTube Music hesabınıza giriş yaparak beğendiğiniz şarkılara, çalma listelerinize ve dinleme geçmişinize erişin.
* **Müzik Oynatıcı:** Arka planda kesintisiz müzik dinleme deneyimi.
* **Arama:** Şarkı, sanatçı, albüm ve çalma listesi araması.
* **Yüksek Kalitede İndirme:** Şarkıları MP3 formatında yüksek kalitede indirebilme (yt-dlp ve FFmpeg altyapısı ile).
* **Modern Arayüz:** Kullanıcı dostu, karanlık tema destekli şık ve modern UI.

## Kurulum

1. **Gereksinimler:** 
   - Python 3.10 veya üzeri
   - [FFmpeg](https://ffmpeg.org/download.html) (Şarkıları dönüştürmek için gereklidir, bilgisayarınızda yüklü ve PATH'e ekli olmalıdır)

2. **Projeyi Klonlayın:**
   ```bash
   git clone https://github.com/KULLANICI_ADINIZ/YtMusicDownloader.git
   cd YtMusicDownloader
   ```

3. **Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Uygulamayı Başlatın:**
   ```bash
   python main.py
   ```

## Kullanım

* Uygulamayı ilk kez açtığınızda **"Tarayıcı ile Giriş Yap"** butonuna tıklayın.
* Açılan ekranda kendi YouTube Music hesabınıza giriş yapın.
* Giriş yaptıktan sonra üstteki onay butonuna basarak arayüze erişin.
* İstediğiniz şarkıyı aratıp dinleyebilir veya indirme ikonuna tıklayarak MP3 olarak bilgisayarınıza indirebilirsiniz.

## Kullanılan Teknolojiler

* [PyQt6](https://pypi.org/project/PyQt6/) - Arayüz
* [ytmusicapi](https://ytmusicapi.readthedocs.io/) - YouTube Music API entegrasyonu
* [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Ses indirme motoru
* [mutagen](https://mutagen.readthedocs.io/) - MP3 ID3 etiketleme (Kapak fotoğrafı vb. ekleme)

## Lisans

Bu proje açık kaynak kodludur.
