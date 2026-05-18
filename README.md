# televideo-linux

Sito web e CLI per leggere notizie reali da Rai Televideo e presentarle come
una cronaca medievale aggiornata in automatico.

Il flusso principale e' la web app Django: un job interno scarica le Ultim'Ora
Rai, salva tutto in SQLite e la pagina si aggiorna da sola mostrando le nuove
notizie. Le lingue disponibili nella UI sono latino, italiano e inglese.

## Funzioni Principali

- Web app Django con stile medievale curato e responsive.
- Notizie reali dal feed pubblico Rai Televideo RSS 101.
- Categorie importate dalla pagina 104 di Televideo e notizie figlie nelle rispettive sezioni.
- Pagina dedicata al SuperEnalotto da pagina 696, con storico estrazioni e andamento montepremi.
- Database SQLite persistente su volume esterno `/data`.
- Job di aggiornamento automatico eseguibile in loop.
- API JSON usata dalla pagina per aggiornarsi senza refresh manuale.
- Selettore lingua: `Latino`, `Italiano`, `English`.
- Container Docker con Gunicorn, job di fetch e volume dati `/data`.
- Makefile per build, run, test e salvataggio immagine in `/tmp`.
- GitHub Action per build, push su GHCR e release del container.
- CLI `./televideo` ancora disponibile per uso terminale.

## Avvio Con Docker

Setup consigliato su server:

```sh
mkdir -p /opt/televideo-docker
docker compose -f /opt/televideo-docker/docker-compose.yml up -d
```

Nel setup preparato in questa macchina trovi:

```text
/opt/televideo-docker/docker-compose.yml
/opt/televideo-docker/chronica.sqlite3
```

Il database SQLite vive fuori dal container, quindi rimane disponibile quando
il container viene fermato, ricreato o aggiornato.

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
      SQLITE_PATH: /data/chronica.sqlite3
      NEWS_REFRESH_SECONDS: "${NEWS_REFRESH_SECONDS:-60}"
      NEWS_FETCH_LIMIT: "${NEWS_FETCH_LIMIT:-12}"
      CATEGORY_FETCH_LIMIT: "${CATEGORY_FETCH_LIMIT:-2}"
      TRANSLATION_TIMEOUT: "${TRANSLATION_TIMEOUT:-8}"
      TRANSLATION_RETRIES: "${TRANSLATION_RETRIES:-1}"
      DJANGO_ALLOWED_HOSTS: "${DJANGO_ALLOWED_HOSTS:-*}"
      DJANGO_SECRET_KEY: "${DJANGO_SECRET_KEY:-televideo-compose-change-me}"
    volumes:
      - /opt/televideo-docker:/data
```

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
python web/manage.py fetch_televideo --loop --interval 60 --limit 20
```

## Configurazione Runtime

Variabili d'ambiente principali:

```text
PORT                  porta HTTP del container, default 8000
SQLITE_PATH           path database, default /data/chronica.sqlite3 nel container
NEWS_REFRESH_SECONDS  frequenza aggiornamento notizie, default 60
NEWS_FETCH_LIMIT      quante notizie conservare a ogni giro, default 12
CATEGORY_FETCH_LIMIT  quante notizie importare per ogni categoria Televideo, default 2
TRANSLATION_TIMEOUT   timeout traduttori online, default 8
TRANSLATION_RETRIES   retry traduttori/feed, default 1
DJANGO_ALLOWED_HOSTS  host consentiti, default *
DJANGO_SECRET_KEY     secret key Django per ambienti pubblici
```

Il container avvia automaticamente:

1. Controllo piano migrazioni Django.
2. Migrazioni Django non distruttive sul database presente in `/data`.
3. Primo fetch di notizie, categorie e SuperEnalotto.
4. Worker in background per aggiornare SQLite.
5. Gunicorn per servire la web app.

Il database non viene cancellato dall'entrypoint. Se `/data/chronica.sqlite3`
esiste gia', Django applica solo le migrazioni mancanti; se non esiste, viene
creato da zero.

## Categorie Televideo

La pagina principale replica le categorie indicate dalla pagina 104 di Rai
Televideo. Il job importa gli indici, segue le pagine figlie quando disponibili
e collega ogni notizia alla categoria corrispondente.

Esempi di categorie:

```text
Ultim'Ora, Politica, Economia, Dall'Italia, Dal Mondo, Culture, Focus
```

Puoi filtrare le notizie dalla barra categorie nella pagina web. Il selettore
lingua cambia anche nomi delle categorie e testi dell'interfaccia.

## SuperEnalotto

Pagina dedicata:

```text
http://localhost:8000/superenalotto/
```

La pagina legge la pagina Televideo 696, salva l'estrazione in SQLite e mostra:

- numero concorso e data;
- combinazione vincente;
- numero Jolly e SuperStar;
- Jackpot;
- Montepremi;
- storico date gia' salvate;
- andamento Jackpot e Montepremi sulle estrazioni presenti nel database.

Lo storico cresce mentre il container resta in funzione nei giorni successivi o
quando viene riavviato con lo stesso volume `/data`.

## Lingue E Traduzioni

La pagina permette di cambiare lingua senza ricaricare:

```text
Latino    resa medievale latina
Italiano  testo originale Televideo con cornice cronachistica
English   traduzione inglese con cornice cronachistica
```

Le traduzioni usano endpoint gratuiti senza API key:

1. Google Translate endpoint non ufficiale.
2. MyMemory.
3. Fallback al testo originale se i servizi non rispondono.

## CLI Terminale

La CLI resta disponibile:

```sh
./televideo
./televideo --medievale 5
./televideo --search Papa
./televideo --news 3 --full
./televideo 100
./televideo 102 --capture
```

Senza argomenti mostra la cronaca medievale live nel terminale. Passando un
numero pagina, per esempio `100`, consulta invece la pagina Televideo classica.

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
televideo                         CLI Python
web/manage.py                     entrypoint Django
web/chronica/                     progetto Django
web/news/                         app notizie, API, job e template
web/news/services.py              fetch RSS, traduzioni, persistenza SQLite
web/news/templates/news/home.html pagina web
web/news/templates/news/superenalotto.html pagina SuperEnalotto
web/news/static/news/             CSS e JavaScript
Dockerfile                        immagine applicativa
docker-compose.yml                compose consigliato con /opt/televideo-docker
docker/entrypoint.sh              migrazioni, worker e Gunicorn
Makefile                          build/run/test/save
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
make test
make save
docker run --rm -p 8000:8000 -v televideo-data:/data televideo-linux:latest
```

## Limiti Noti

- Gli endpoint Rai sono pubblici ma non API garantite.
- Gli endpoint gratuiti di traduzione possono cambiare o limitare il traffico.
- Il latino e' una resa automatica medievaleggiante, non una traduzione filologica.
- La release automatica richiede un runner self-hosted gia' registrato su GitHub.

## Licenza

MIT. Vedi `LICENSE`.
