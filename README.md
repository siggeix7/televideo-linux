# televideo-linux

Sito web e CLI per leggere notizie reali da Rai Televideo con uno stile
mediavideo/teletext retro: sfondo nero, font monospace e palette di colori CRT.

Il flusso principale e' la web app Django: un job interno scarica le Ultim'Ora
Rai, salva tutto in PostgreSQL 18 e la pagina si aggiorna da sola mostrando le nuove
notizie.

## Funzioni Principali

- Web app Django con stile mediavideo retro curato, responsive e design system a token.
- Notizie reali dal feed pubblico Rai Televideo RSS 101.
- Archivio news unico, senza filtri per categoria, raggruppato per giorno e filtrabile da calendario.
- Barra di ricerca client-side per filtrare le notizie nella pagina principale.
- Storico notizie persistente: le notizie restano salvate anche dopo che spariscono da Televideo.
- Paginazione automatica quando lo storico contiene molte notizie.
- Pagina dedicata al SuperEnalotto da pagina 696, con storico estrazioni e andamento montepremi.
- Sezioni Televideo dedicate per TV, cultura, ambiente/scienza, lavoro, sport, meteo, viaggi, giochi e regioni.
- Mappa SVG interattiva dell'Italia nella sezione meteo: ogni regione e' cliccabile e apre il Televideo regionale; con OpenWeatherMap configurato il meteo usa previsioni a 5 giorni, min/max e alba/tramonto.
- Tabelle dati strutturate: classifica Serie A, risultati, palinsesto TV, Auditel, stazioni meteo, ruote Lotto.
- Articoli multi-pagina: il parser fonde automaticamente le sottopagine Televideo in un unico articolo.
- Cache delle pagine Televideo non-news, separata dallo storico notizie.
- Lotto da pagina 691 con parsing delle ruote e SuperEnalotto nella pagina giochi.
- PostgreSQL 18 come database predefinito, con dati persistenti su volume esterno `/data`.
- Job di aggiornamento automatico con worker paralleli (news + sezioni).
- API JSON usata dalla pagina per aggiornarsi senza refresh manuale.
- Tag versione visibile nel footer, utile per verificare quale container e' in esecuzione.
- Home renderizzata anche lato server, con ricerca condivisibile via URL e fallback senza JavaScript.
- Skeleton loading con effetto shimmer, retry automatico (3 tentativi) e pagine di errore 404/500.
- Meta tag Open Graph / Twitter Card e favicon SVG.
- Container Docker con Gunicorn, worker background e volume dati `/data`.
- Makefile per build, run, test e salvataggio immagine in `/tmp`.
- GitHub Action per build, push su GHCR e release del container.
- CLI `./televideo` ancora disponibile per uso terminale.
- Test automatizzati per modelli Django, viste, asset statici e worker.

## Avvio Con Docker

Setup consigliato su server:

```sh
mkdir -p /opt/televideo-docker
chown -R 1000:1000 /opt/televideo-docker
docker compose -f /opt/televideo-docker/docker-compose.yml up -d
```

Nel setup preparato in questa macchina trovi:

```text
/opt/televideo-docker/docker-compose.yml
/opt/televideo-docker/postgresql/
/opt/televideo-docker/postgresql/
```

Il database vive fuori dal container, quindi rimane disponibile quando
il container viene fermato, ricreato o aggiornato. Di default usa PostgreSQL 18 (embedded nel container); e'
possibile usare SQLite per sviluppo locale (POSTGRES_HOST="").

Docker Compose consigliato:

```yaml
services:
  televideo:
    image: televideo-linux:latest
    container_name: televideo-web
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"
    environment:
      NEWS_REFRESH_SECONDS: "${NEWS_REFRESH_SECONDS:-1200}"
      NEWS_FETCH_LIMIT: "${NEWS_FETCH_LIMIT:-30}"
      CATEGORY_FETCH_LIMIT: "${CATEGORY_FETCH_LIMIT:-2}"
      TELETEXT_SECTION_REFRESH_SECONDS: "${TELETEXT_SECTION_REFRESH_SECONDS:-21600}"
      METEO_SECTION_REFRESH_SECONDS: "${METEO_SECTION_REFRESH_SECONDS:-3600}"
      OPENWEATHER_API_KEY: "${OPENWEATHER_API_KEY:-}"
      OPENWEATHER_REFRESH_CHECK_SECONDS: "${OPENWEATHER_REFRESH_CHECK_SECONDS:-9000}"
      OPENWEATHER_STALE_SECONDS: "${OPENWEATHER_STALE_SECONDS:-9000}"
      OPENWEATHER_MAX_CALLS_PER_MINUTE: "${OPENWEATHER_MAX_CALLS_PER_MINUTE:-40}"
      OPENWEATHER_BATCH_SIZE: "${OPENWEATHER_BATCH_SIZE:-200}"
      POSTGRES_HOST: "${POSTGRES_HOST:-localhost}"
      POSTGRES_DB: "${POSTGRES_DB:-televideo}"
      POSTGRES_USER: "${POSTGRES_USER:-televideo}"
      POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:-televideo}"
      POSTGRES_PORT: "${POSTGRES_PORT:-5432}"
      PUBLIC_SITE_URL: "${PUBLIC_SITE_URL:-}"
      DJANGO_DEBUG: "${DJANGO_DEBUG:-false}"
      DJANGO_ALLOWED_HOSTS: "${DJANGO_ALLOWED_HOSTS:-*}"
      DJANGO_CSRF_TRUSTED_ORIGINS: "${DJANGO_CSRF_TRUSTED_ORIGINS:-}"
      DJANGO_ADMIN_ENABLED: "${DJANGO_ADMIN_ENABLED:-false}"
      DJANGO_USE_X_FORWARDED_HOST: "${DJANGO_USE_X_FORWARDED_HOST:-true}"
      DJANGO_SECURE_PROXY_SSL_HEADER: "${DJANGO_SECURE_PROXY_SSL_HEADER:-true}"
      DJANGO_SECURE_SSL_REDIRECT: "${DJANGO_SECURE_SSL_REDIRECT:-false}"
      DJANGO_COOKIE_SECURE: "${DJANGO_COOKIE_SECURE:-false}"
      DJANGO_SECURE_HSTS_SECONDS: "${DJANGO_SECURE_HSTS_SECONDS:-0}"
      DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS: "${DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS:-false}"
      DJANGO_SECURE_HSTS_PRELOAD: "${DJANGO_SECURE_HSTS_PRELOAD:-false}"
      DJANGO_SECRET_KEY: "${DJANGO_SECRET_KEY:-televideo-compose-change-me}"
    volumes:
      - /opt/televideo-docker:/data
```

Per produzione dietro Nginx Proxy Manager, crea `/opt/televideo-docker/.env`:

```env
PORT=8000
NEWS_REFRESH_SECONDS=1200
NEWS_FETCH_LIMIT=30
CATEGORY_FETCH_LIMIT=2
TELETEXT_SECTION_REFRESH_SECONDS=21600
METEO_SECTION_REFRESH_SECONDS=3600
OPENWEATHER_API_KEY=
OPENWEATHER_REFRESH_CHECK_SECONDS=9000
OPENWEATHER_STALE_SECONDS=9000
OPENWEATHER_MAX_CALLS_PER_MINUTE=40
OPENWEATHER_BATCH_SIZE=200
POSTGRES_HOST=localhost
POSTGRES_DB=televideo
POSTGRES_USER=televideo
POSTGRES_PASSWORD=televideo
POSTGRES_PORT=5432
PUBLIC_SITE_URL=https://televideo.example.com

DJANGO_DEBUG=false
DJANGO_ADMIN_ENABLED=false
DJANGO_ALLOWED_HOSTS=televideo.example.com,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://televideo.example.com
DJANGO_USE_X_FORWARDED_HOST=true
DJANGO_SECURE_PROXY_SSL_HEADER=true
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_COOKIE_SECURE=true
DJANGO_SECURE_HSTS_SECONDS=86400
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=false
DJANGO_SECURE_HSTS_PRELOAD=false
DJANGO_SECRET_KEY=cambia-questa-stringa-lunga-e-casuale
```

Nel deploy pubblico l'admin Django e' disabilitato di default. Riabilitalo solo
se serve davvero impostando `DJANGO_ADMIN_ENABLED=true` e proteggendolo a monte
con allowlist IP o autenticazione aggiuntiva nel reverse proxy.

In Nginx Proxy Manager configura un Proxy Host verso:

```text
Forward Hostname / IP: IP_DEL_SERVER_DOCKER
Forward Port: 8000
Scheme: http
Websockets Support: non necessario
Block Common Exploits: attivo
SSL: Request a new SSL Certificate
Force SSL: attivo
HTTP/2 Support: attivo
```

Il container espone solo HTTP. HTTPS e certificato restano responsabilita' del
reverse proxy.

Per aggiornare l'immagine senza perdere dati:

```sh
docker compose -f /opt/televideo-docker/docker-compose.yml pull
docker compose -f /opt/televideo-docker/docker-compose.yml up -d
```

Se stai usando l'immagine buildata localmente con `make save`, basta ricreare il
servizio dopo il nuovo build:

```sh
make save
docker compose -f /opt/televideo-docker/docker-compose.yml up -d --force-recreate
```

Build dell'immagine e salvataggio automatico in `/tmp`:

```sh
make
```

Il target default esegue `make save` e produce:

```text
/tmp/televideo-linux-latest.tar
```

Avvio locale del sito:

```sh
make run
```

Poi apri:

```text
http://localhost:8000
```

Avvio diretto con Docker, utile per provarlo senza compose:

```sh
docker run -d \
  --name televideo-web \
  -p 8000:8000 \
  -v televideo-data:/data \
  televideo-linux:latest
```

Aggiornamento del container mantenendo database e storico:

```sh
docker stop televideo-web
docker rm televideo-web
docker run -d --name televideo-web -p 8000:8000 -v televideo-data:/data televideo-linux:latest
```

Se preferisci un path esplicito sul filesystem host:

```sh
mkdir -p /srv/televideo-data
docker run -d --name televideo-web -p 8000:8000 -v /srv/televideo-data:/data televideo-linux:latest
```

Caricare l'immagine salvata in `/tmp` su un'altra macchina:

```sh
docker load -i /tmp/televideo-linux-latest.tar
docker run --rm -p 8000:8000 -v televideo-data:/data televideo-linux:latest
```

## Target Makefile

```text
make build       builda l'immagine Docker
make save        builda e salva /tmp/televideo-linux-latest.tar
make run         avvia il sito su http://localhost:8000
make shell       apre una shell Django nel container
make test        esegue check Python/Django locali
make clean       rimuove l'archivio immagine da /tmp
```

Variabili utili:

```sh
make save IMAGE=chronica TAG=v1 TMP_IMAGE=/tmp/chronica-v1.tar
make run PORT=8080
```

## Avvio Locale Senza Docker

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python web/manage.py migrate
python web/manage.py fetch_televideo --once --limit 5
python web/manage.py runserver
```

Job di aggiornamento continuo:

```sh
python web/manage.py fetch_televideo --loop --interval 1200 --limit 30
```

## Configurazione Runtime

Variabili d'ambiente principali:

```text
PORT                  porta HTTP del container, default 8000
NEWS_REFRESH_SECONDS  frequenza aggiornamento notizie, default 1200 (20 minuti)
NEWS_FETCH_LIMIT      quante notizie conservare a ogni giro, default 30
CATEGORY_FETCH_LIMIT  quante notizie importare per ogni categoria Televideo, default 2
TELETEXT_SECTION_REFRESH_SECONDS frequenza cache sezioni Televideo dedicate, default 21600 (6 ore)
METEO_SECTION_REFRESH_SECONDS frequenza refresh dati meteo, default 3600 (1 ora)
OPENWEATHER_API_KEY chiave API OpenWeatherMap; se vuota il fallback meteo e' disabilitato
OPENWEATHER_REFRESH_CHECK_SECONDS frequenza check fallback meteo, default 9000
OPENWEATHER_STALE_SECONDS eta' massima cache meteo OpenWeatherMap, default 9000 (2.5 ore)
OPENWEATHER_MAX_CALLS_PER_MINUTE limite interno richieste OpenWeatherMap, default 40
OPENWEATHER_BATCH_SIZE massimo capoluoghi aggiornati per check, default 200
POSTGRES_HOST         hostname PostgreSQL, default localhost
POSTGRES_DB           nome database PostgreSQL, default televideo
POSTGRES_USER         utente PostgreSQL, default televideo
POSTGRES_PASSWORD     password PostgreSQL, default televideo
POSTGRES_PORT         porta PostgreSQL, default 5432
APP_VERSION           tag mostrato nel footer, impostato automaticamente dalla release container
DJANGO_DEBUG          debug Django, default false
DJANGO_ALLOWED_HOSTS  host consentiti, default *
DJANGO_CSRF_TRUSTED_ORIGINS origini HTTPS fidate per admin/form, es. https://dominio
DJANGO_ADMIN_ENABLED  espone /admin/, default false
DJANGO_USE_X_FORWARDED_HOST legge X-Forwarded-Host dal proxy, default true
DJANGO_SECURE_PROXY_SSL_HEADER considera HTTPS se X-Forwarded-Proto=https, default true
DJANGO_SECURE_SSL_REDIRECT redirect HTTPS lato Django, default false; usa true se il proxy invia X-Forwarded-Proto
DJANGO_COOKIE_SECURE cookie solo HTTPS, consigliato true dietro NPM pubblico
DJANGO_SECURE_HSTS_SECONDS abilita HSTS se maggiore di 0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS include i sottodomini nell'HSTS
DJANGO_SECURE_HSTS_PRELOAD abilita il flag preload HSTS
DJANGO_SECRET_KEY     secret key Django per ambienti pubblici
```

### Passare a PostgreSQL 18

Il progetto usa PostgreSQL 18 come database predefinito;
per attivarlo aggiungi al file `.env`:

```env
POSTGRES_HOST=localhost
POSTGRES_DB=televideo
POSTGRES_USER=televideo
POSTGRES_PASSWORD=televideo
POSTGRES_PORT=5432
```

Il container avvia automaticamente PostgreSQL alla partenza e inizializza il
data directory in `/data/postgresql/` (mappato su
`/opt/televideo-docker/postgresql/`). Se il data directory esiste gia', viene
riutilizzato.

Per migrare i dati esistenti da SQLite:

```sh
docker exec televideo-web python web/manage.py migrate_to_postgresql
```

Il database PostgreSQL non
viene modificato. Per tornare a SQLite basta rimuovere `POSTGRES_HOST` dal
`.env` e ricreare il container.

Il container avvia automaticamente:

1. Controllo piano migrazioni Django.
2. Migrazioni Django non distruttive sul database presente in `/data`.
3. Primo fetch di notizie, categorie e SuperEnalotto.
4. Worker in background per aggiornare il database (news, sezioni e, se configurato, OpenWeatherMap).
5. Gunicorn per servire la web app.

Il database non viene cancellato dall'entrypoint. Django applica solo le
migrazioni mancanti sul database esistente; se il database non esiste, viene
creato da zero dalla entrypoint.

Endpoint healthcheck:

```text
http://localhost:8000/healthz/
```

Il Dockerfile include un `HEALTHCHECK` che interroga questo endpoint.

## Archivio News

La pagina principale mostra un archivio unico delle notizie, senza divisioni per
categoria. Le card sono raggruppate per giorno e il campo data permette di
aprire direttamente le notizie pubblicate in una giornata specifica.

Il job continua a importare gli indici dalla pagina 104 di Rai Televideo e segue
le pagine figlie quando disponibili, ma le categorie restano solo un dettaglio
interno usato per recuperare piu' notizie dall'origine Rai.

Le pagine di servizio o tabellari, come Almanacco, Meteo, Temperature e
Viabilita', non vengono mostrate come notizie: Televideo le espone in formati
troppo diversi dagli articoli editoriali e generavano schede poco leggibili.

Le notizie non vengono eliminate quando non compaiono piu' su Televideo: restano
nello storico e la pagina principale usa una paginazione lato API/UI per
non caricare troppe schede insieme.

## Sezioni Dedicate

Le pagine Televideo non adatte a diventare notizie sono integrate in sezioni
separate, con cache propria e layout dedicato:

```text
/tv/          guida TV con card film, palinsesto, Auditel, radio
/cultura/     libri, cinema, teatro, concerti, eventi, mostre (articoli multi-pagina)
/ambiente/    ambiente, scienza, salute, CNR, INAF, ASviS
/lavoro/      concorsi, Gazzetta, formazione, agenzie, eventi lavoro
/sport/       classifica Serie A con colori posizione + griglia risultati
/meteo/       mappa Italia interattiva, stazioni meteo, barre temperatura
/viaggi/      viaggiare sicuri, FAI, Touring Club, itinerari, mare
/giochi/      griglia ruote Lotto, SuperEnalotto e giochi Televideo
/regioni/     Televideo regionale con selettore regione
```

Queste sezioni non vengono mischiate con la cronaca principale. I dati
vengono parsati lato server dai formatters (classifica, risultati, palinsesto,
meteo, Lotto, Auditel) e mostrati in tabelle e card strutturate.

Le pagine sezioni rispondono in ~150ms grazie alla cache pre-popolata
dal worker `fetch_sections`, invece dei 30+ secondi di una chiamata diretta
agli endpoint Rai.

### Fallback Meteo OpenWeatherMap

Senza `OPENWEATHER_API_KEY`, la mappa meteo usa i dati disponibili da Rai
Televideo. Con `OPENWEATHER_API_KEY` configurata, le informazioni meteo vengono
prese solo dalla cache OpenWeatherMap e la raccolta meteo Televideo viene
saltata. I dati mostrati includono stato corrente, slot della giornata,
previsioni dei giorni successivi, minime/massime e alba/tramonto.

Per abilitare la funzione imposta nel file `.env` usato da Docker Compose:

```env
OPENWEATHER_API_KEY=la-tua-api-key-openweathermap
```

La chiave non va salvata nel repository. Senza `OPENWEATHER_API_KEY` il sito
continua a usare solo Televideo per la sezione meteo.

Il worker non chiama l'API durante le visite degli utenti: legge e aggiorna una
cache. Ogni 2.5 ore (o OPENWEATHER_REFRESH_CHECK_SECONDS) aggiorna i capoluoghi di provincia (110 circa),
con un rate limiter che non supera `OPENWEATHER_MAX_CALLS_PER_MINUTE` richieste
al minuto (default 40), cosi' il piano gratuito non viene stressato.

Per forzare l'aggiornamento immediato di tutti i dati meteo
(Televideo + OpenWeatherMap), esegui dentro al container:

```sh
docker exec televideo-web python web/manage.py force_refresh_meteo
```

oppure, se il container ha lo script sotto `/usr/local/bin/refresh-meteo`:

```sh
docker exec televideo-web refresh-meteo
```

## SuperEnalotto

Pagina dedicata:

```text
http://localhost:8000/superenalotto/
```

La pagina legge la pagina Televideo 696, salva l'estrazione e mostra:
- numero concorso e data;
- combinazione vincente;
- numero Jolly e SuperStar;
- Jackpot;
- Montepremi;
- storico date gia' salvate;
- andamento Jackpot e Montepremi sulle estrazioni presenti nel database.

Lo storico cresce mentre il container resta in funzione nei giorni successivi o
quando viene riavviato con lo stesso volume `/data`.

## CLI Terminale

La CLI resta disponibile:

```sh
./televideo
./televideo 5
./televideo --search Papa
./televideo --news 3 --full
./televideo 100
./televideo 102 --capture
```

Senza argomenti mostra le notizie live nel terminale. Passando un numero
pagina, per esempio `100`, consulta invece la pagina Televideo classica.

## Fonte Dati

Feed principale:

```text
https://www.televideo.rai.it/televideo/pub/rss101.xml
https://www.servizitelevideo.rai.it/televideo/pub/rss101.xml
```

Endpoint secondari usati dalla CLI per le pagine classiche:

```text
https://www.televideo.rai.it/televideo/pub/solotesto.jsp?pagina=100
https://www.televideo.rai.it/televideo/pub/catturaSottopagine.jsp?pagina=102&regione=
https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-100.png
```

## GitHub Action E Release Container

Workflow inclusa:

```text
.github/workflows/container-release.yml
```

La workflow gira su runner self-hosted Linux:

```yaml
runs-on: [self-hosted, linux]
```

Quando fai push di un tag `v*`, la workflow:

1. Builda l'immagine Docker.
2. La tagga come `ghcr.io/<owner>/<repo>:<tag>` e `latest`.
3. Fa push su GitHub Container Registry.
4. Salva anche un archivio in `/tmp` sul runner.
5. Carica l'archivio come artifact.
6. Crea una GitHub Release con l'archivio allegato.

Esempio release:

```sh
git tag v0.1.0
git push origin v0.1.0
```

Per usare il container LXC come runner devi registrarlo dalle impostazioni del
repository GitHub: `Settings -> Actions -> Runners -> New self-hosted runner`.
Serve il token generato da GitHub in quella pagina. Il runner deve avere Docker
installato e l'utente del runner deve poter eseguire `docker build` e
`docker push`.

## Architettura

```text
televideo                                  CLI Python
web/manage.py                              entrypoint Django
web/chronica/                              progetto Django
web/news/                                  app notizie, API, job e template
web/news/formatters.py                     parser strutturati: Serie A, TV, meteo, Lotto, Auditel
web/news/models.py                         modelli Django (NewsItem, Category, SuperEnalotto, Lotto, Snapshot)
web/news/services/                         servizi modulari
web/news/services/constants.py             definizioni pagine e sezioni Televideo
web/news/services/fetcher.py               fetch HTTP da endpoint Rai
web/news/services/parser.py                parsing RSS e pagine Televideo
web/news/services/updater.py               persistenza dati e logica aggiornamento
web/news/templates/news/home.html          pagina principale
web/news/templates/news/superenalotto.html pagina SuperEnalotto
web/news/templates/news/regions.html       Televideo regionale
web/news/templates/news/_meteo_map.html    mappa Italia interattiva SVG
web/news/templates/news/section.html       base sezioni dedicate
web/news/templates/news/section_*.html     layout specifici per TV, sport, meteo, cultura, giochi
web/news/templates/news/error.html         pagine 404/500
web/news/static/news/                      CSS e JavaScript
web/news/tests/                            test modelli e viste (19 test)
Dockerfile                                 immagine applicativa
docker-compose.yml                         compose consigliato con /opt/televideo-docker
docker/entrypoint.sh                       migrazioni, worker paralleli e Gunicorn
Makefile                                   build/run/test/save
```

## Verifica

Comandi usati per testare il progetto:

```sh
python3 -m py_compile televideo
python web/manage.py check
python web/manage.py makemigrations --check --dry-run
python web/manage.py migrate --noinput
python web/manage.py fetch_televideo --once --limit 3
python web/manage.py collectstatic --noinput
python web/manage.py test news
make test
make save
docker run --rm -p 8000:8000 -v televideo-data:/data televideo-linux:latest
```

## Limiti Noti

- Gli endpoint Rai sono pubblici ma non API garantite.
- La release automatica richiede un runner self-hosted gia' registrato su GitHub.

## Licenza

MIT. Vedi `LICENSE`.
