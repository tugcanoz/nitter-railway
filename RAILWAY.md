# Railway üzerinde Nitter + RSS

Bu depo, [zedeus/nitter](https://github.com/zedeus/nitter) kaynak kodunu Railway üzerinde RSS açık çalıştırmak için yapılandırır. AGPL-3.0 lisansı korunur. Kaynak sürüm: `376f14908e27e095049bbbeb648e742501144010`.

## Gereksinimler

- Railway hesabı ve aynı Railway projesinde bir Redis servisi.
- Geçerli bir X hesabının `auth_token` ve `ct0` oturum çerezleri. Bunlar olmadan canlı RSS verisi alınamaz. Çerezleri GitHub'a veya sohbetlere koymayın; yalnızca Railway Variables içine girin.
- GitHub'a yüklenmesi Railway'de otomatik olarak proje oluşturmaz. Aşağıdaki kurulum bir kez yapılmalıdır.

## Kurulum

1. Railway'de **New Project → Deploy from GitHub repo** ile `tugcanoz/nitter-railway` deposunu seçin. Railway uygulamasının bu depoya erişimi olmalı. Root Directory boş kalsın; `railway.json`, `Dockerfile.railway` dosyasını seçer. Start Command eklemeyin.
2. Aynı projeye **New → Database → Redis** ekleyin. Servis adı `Redis` olsun; başka bir ad kullanırsanız aşağıdaki referansları değiştirin.
3. Nitter servisinde **Settings → Networking → Generate Domain** ile bir alan adı oluşturun. Hedef port için `8080` kullanın ve Variables'a `PORT=8080` ekleyin. Özel alan adı kullanıyorsanız `NITTER_HOSTNAME` değerini protokol olmadan bu alan adına ayarlayın.
4. Nitter servisinin **Variables** bölümünde şu değerleri ekleyin:

| Değişken | Değer |
| --- | --- |
| `PORT` | `8080` |
| `REDISHOST` | `${{Redis.REDISHOST}}` |
| `REDISPORT` | `${{Redis.REDISPORT}}` |
| `REDISPASSWORD` | `${{Redis.REDISPASSWORD}}` |
| `NITTER_HMAC_KEY` | Bir kez üretilmiş en az 32 karakterlik rastgele gizli değer |
| `X_USERNAME` | Çerezlerin ait olduğu X kullanıcı adı, `@` olmadan |
| `X_AUTH_TOKEN` | X `auth_token` çerezinin değeri |
| `X_CT0` | Aynı oturumun `ct0` çerezinin değeri |

`RAILWAY_PUBLIC_DOMAIN`, Railway tarafından sağlanır. Yoksa `NITTER_HOSTNAME=servisin.up.railway.app` ekleyin. HMAC anahtarı için yerel Python'da `python -c "import secrets; print(secrets.token_hex(32))"` çalıştırabilirsiniz. Anahtarı deploylar arasında sabit tutun.

5. Değişiklikleri deploy edin. Eksik değişken varsa servis adı belirtilen bir hata ile durur; önce Variables'ı tamamlayıp yeniden deploy edin. Redis bağlantısı kurulduktan sonra ana sayfa açılmalıdır.
6. Aşağıdaki RSS adreslerinden birini tarayıcıda açıp XML geldiğini doğrulayın ve RSS okuyucunuza ekleyin. Healthcheck yalnızca uygulamanın açılmasını kontrol eder; X oturumunun çalıştığını garanti etmez.

## X çerezlerini alma

Kendi tarayıcınızda `x.com` üzerinde oturum açın. Geliştirici Araçları → Application/Storage → Cookies → `https://x.com` altında `auth_token` ve `ct0` değerlerini bulun. Her ikisini de aynı oturumdan kopyalayın ve Railway'de ilgili gizli değişkenlere girin. Çerezlerin süresi dolarsa veya oturum kapatılırsa değerleri yenileyip redeploy edin.

Birden fazla oturum için tek tek `X_*` değişkenleri yerine `NITTER_SESSIONS` kullanabilirsiniz. Değer, her satırda bir JSON nesnesi bulunan JSONL olmalıdır (JSON dizisi değil):

```jsonl
{"kind":"cookie","username":"YOUR_USERNAME","id":"0","auth_token":"YOUR_AUTH_TOKEN","ct0":"YOUR_CT0"}
```

`NITTER_SESSIONS` tanımlıysa önceliklidir. `id` isteğe bağlı sayısal X hesap kimliğidir; belirtilmezse `0` kullanılır. `X_USERNAME`, veri kaynağı oturumudur; aşağıdaki RSS adresinde takip etmek istediğiniz farklı bir herkese açık hesabı kullanabilirsiniz.

## RSS adresleri

`ALAN_ADIN` yerine Railway alan adını, `KULLANICI` yerine takip edilecek kullanıcı adını yazın (`@` eklemeyin):

```text
https://ALAN_ADIN/KULLANICI/rss
https://ALAN_ADIN/KULLANICI/with_replies/rss
https://ALAN_ADIN/KULLANICI/media/rss
https://ALAN_ADIN/search/rss?f=tweets&q=kelime
https://ALAN_ADIN/i/lists/LISTE_ID/rss
```

RSS önbelleği varsayılan 15 dakikadır; okuyucuyu 15 dakika veya daha uzun aralıklarla yenilemeye ayarlayın. İsteğe bağlı `RSS_CACHE_MINUTES` değişkeni 1–1440 aralığındadır. Her yenilemede tüm geçmiş tweetlerin aktarılması beklenmemelidir.

## İşletim ve sorun giderme

- Bu yapılandırma bir Nitter ve bir Redis servisi kullanır. `railway.json` Redis'i kendisi oluşturmaz. Nitter için disk volume gerekmez; yapılandırma başlangıçta ortam değişkenlerinden üretilir.
- Railway HTTPS'i sonlandırır; Nitter `0.0.0.0:$PORT` üzerinde HTTP dinler ve bağlantıları HTTPS olarak üretir. Yerelde HTTP kullanmak için `NITTER_HTTPS=false` ayarlanabilir.
- `Missing required variable`: belirtilen değişkeni ekleyin. Alan adı için `https://` veya `/` kullanmayın.
- Redis bağlantı hatası: iki servisin aynı proje/ortamda olduğunu, referans değişkenlerini ve Redis durumunu kontrol edin. `REDIS_URL` yerine yukarıdaki üç değişken kullanılır.
- `429`, oturum yok veya boş RSS: X oturumunu ve hesap durumunu kontrol edin; gerekirse çerezleri yenileyin ve istek sıklığını azaltın. Arama, listeler ve kullanıcı akışları X tarafından farklı kısıtlamalara tabi olabilir.
- Nitter upstream deposu 11 Eylül 2026 itibarıyla arşivlenmiştir. X'in resmi olmayan API'sindeki değişiklikler akışları bozabilir; Railway'de servis açılması canlı RSS'in çalışacağını tek başına garanti etmez.
- Gizli dosyalar `.gitignore` ve `.dockerignore` ile hariç tutulur; çalışma dosyaları runtime dizinine yalnızca servis kullanıcısı erişecek şekilde yazılır. Debug kapalıdır.
- Bu forkta upstream DockerHub yayın workflow'ları için gerekli sırlar yoktur. GitHub Actions kapalı tutulur; derleme Railway Dockerfile üzerinden yapılır.

## Doğrulama

```sh
python -m unittest discover -s railway -p 'test_*.py' -v
docker build -f Dockerfile.railway -t nitter-railway .
```

İlk komut port/HTTPS/RSS ayarlarını, çerez dosyalarını, yanlış girdileri ve gizli değerlerin hata mesajlarına taşınmamasını sınar. Docker derlemesi ve geçerli X oturumuyla canlı RSS testi ayrıca yapılmalıdır.

Resmi kaynaklar: [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles), [Config as Code](https://docs.railway.com/config-as-code/reference), [Nitter](https://github.com/zedeus/nitter).
