# televideo-linux

Notizie reali e aggiornate da Rai Televideo, lette dal terminale e trasformate
in una piccola cronaca medievale in latino medievaleggiante.

Il comando principale e' ora semplicemente:

```sh
./televideo
```

Senza argomenti il programma scarica il feed live Ultim'Ora di Rai Televideo,
prende le notizie piu' recenti e le presenta come `Chronica Televidei`, con
titoli tradotti in latino, data originale della fonte e testo riassunto in stile
da cronaca.

## Cosa Fa

- Legge notizie reali dal feed RSS pubblico Rai Televideo pagina 101.
- Mostra di default una cronaca medievale delle ultime notizie live.
- Traduce titoli e sintesi in latino tramite servizi online gratuiti.
- Mantiene un fallback locale se la traduzione online non risponde.
- Permette ricerca nel feed Ultim'Ora con `--search`.
- Permette aggiornamento continuo con `--watch`.
- Salva la cronaca in file di testo con `-o` / `--output`.
- Mantiene accesso secondario alle pagine classiche Rai Televideo.

## Requisiti

- Python 3.
- Nessuna dipendenza `pip`.
- Connessione Internet per leggere le notizie live Rai.
- `chafa` solo se vuoi visualizzare le pagine grafiche con `--image`.

## Installazione

Uso locale:

```sh
chmod +x televideo
./televideo
```

Installazione come comando di sistema:

```sh
sudo install -m 755 televideo /usr/local/bin/televideo
televideo
```

## Uso Principale

Cronaca medievale live, default 5 notizie:

```sh
./televideo
./televideo --medievale
./televideo --medieval-summary
```

Numero di notizie:

```sh
./televideo --medievale 8
./televideo --medieval-summary 3
```

Ricerca nelle Ultim'Ora, sempre in stile cronaca medievale se non specifichi
`--news`:

```sh
./televideo --search Papa
./televideo --search energia --medievale 10
```

Aggiornamento automatico:

```sh
./televideo --watch 60
./televideo --medievale 5 --watch 30 --count 3
```

Salvataggio in file:

```sh
./televideo -o chronica.txt
./televideo --medievale 10 --search governo -o governo.txt
```

Mostrare anche URL sorgente RSS e link delle singole notizie:

```sh
./televideo --url
```

## Traduzione Latina

Il default e' `--latin-translator auto`:

```sh
./televideo --latin-translator auto
```

Ordine usato in modalita `auto`:

1. Google Translate endpoint gratuito non ufficiale, `it -> la`.
2. MyMemory, `it|la`.
3. Fallback locale offline.

Puoi forzare un traduttore:

```sh
./televideo --latin-translator google
./televideo --latin-translator mymemory
./televideo --latin-translator local
```

Nota: non esiste qui un servizio gratuito affidabile che dichiari esplicitamente
"latino medievale". Lo script traduce in latino e applica poi una resa da
cronaca medievale, con formule come `Chronica`, `Capitulum`, `In chronicis
scriptum est` e grafia semplificata.

## Output Originale Delle Notizie

Se vuoi leggere il feed Rai senza resa medievale:

```sh
./televideo --news
./televideo --news 5
./televideo --news 3 --full
./televideo --news 20 --search Tajani
```

## Pagine Televideo Classiche

La consultazione delle pagine resta disponibile, ma non e' piu' il flusso
principale. Passa un numero pagina per usare la modalita classica:

```sh
./televideo 100
./televideo 101 -s 1
./televideo 300 -r Lazio
./televideo 102 --capture
```

Pagina grafica con `chafa` se installato:

```sh
./televideo 100 --image
./televideo 100 --image --url
```

Se `chafa` non e' disponibile, `--image` stampa l'URL PNG ufficiale Rai.

## Opzioni CLI

```text
page                  pagina Televideo classica da consultare, es. 100
--medieval-summary [N]
--medievale [N]       cronaca medievale live delle ultime N notizie, default 5
--latin-translator    auto, google, mymemory o local, default auto
--news [N]            ultime N notizie RSS in formato originale, default 10
--full                con --news mostra anche il testo completo
--search TEXT         filtra le Ultim'Ora; da solo usa la cronaca medievale
--watch SECONDS       aggiorna l'output ogni N secondi
--count N             numero di aggiornamenti da fare con --watch
-o, --output FILE     salva l'output testuale in un file
--url                 stampa URL sorgente RSS o pagina Rai
-s, --subpage         sottopagina Televideo classica, es. 1
-r, --region          regione Rai, es. Lazio, Lombardia, Emilia-Romagna
--image               mostra la pagina grafica con chafa, se installato
--capture             cattura sottopagine disponibili della pagina
--timeout SECONDS     timeout per host in secondi, default 10
--retries N           ritentativi dopo il primo giro, default 1
```

`--image`, `--capture`, `--news` e `--medieval-summary` sono modalita
alternative: usane una sola per volta.

## Fonte Dati

Le notizie arrivano dal feed pubblico Ultim'Ora Rai Televideo:

```text
https://www.televideo.rai.it/televideo/pub/rss101.xml
https://www.servizitelevideo.rai.it/televideo/pub/rss101.xml
```

Il programma prova entrambi gli host Rai e usa `--timeout` / `--retries` per
gestire momenti in cui un endpoint risponde lentamente.

Endpoint secondari usati per le pagine classiche:

```text
https://www.televideo.rai.it/televideo/pub/solotesto.jsp?pagina=100
https://www.televideo.rai.it/televideo/pub/catturaSottopagine.jsp?pagina=102&regione=
https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-100.png
```

## Regioni Supportate

Puoi passare il nome della regione con `-r` / `--region` per le pagine
classiche regionali.

Esempi accettati:

```text
Abruzzo, Alto-Adige, Basilicata, Calabria, Campania, Emilia-Romagna,
Friuli Venezia Giulia, Lazio, Liguria, Lombardia, Marche, Molise,
Piemonte, Puglia, Sardegna, Sicilia, Toscana, Trentino, Umbria,
Valle d'Aosta, Veneto
```

Sono accettate anche varianti pratiche come `emilia`, `emilia-romagna`,
`friuli` e `valle-aosta`.

## Architettura

File principali:

```text
televideo    CLI Python principale
README.md    documentazione del progetto
LICENSE      licenza MIT
```

Scelte tecniche:

- `argparse` per l'interfaccia CLI.
- `urllib.request` per HTTP/HTTPS senza dipendenze esterne.
- `xml.etree.ElementTree` per leggere il feed RSS Rai.
- Fallback tra host Rai ufficiali e mirror `servizitelevideo`.
- Traduzione online opzionale senza chiavi API.
- Regex mirate per estrarre il blocco `<pre>` dalle pagine solo testo Rai.
- `tempfile` e `subprocess` per passare i PNG temporanei a `chafa`.

## Verifica

Comandi usati per testare il progetto:

```sh
python3 -m py_compile televideo
./televideo
./televideo --help
./televideo --medievale 2 --latin-translator google
./televideo --search Papa --latin-translator local
./televideo --news 2
./televideo --news 1 --full
./televideo 100
./televideo 102 --capture
./televideo --medievale 1 --watch 1 --count 1 --latin-translator local
```

## Limiti Noti

- Il progetto dipende dagli endpoint pubblici Rai, che non sono API garantite.
- Gli endpoint gratuiti di traduzione possono cambiare, limitare o degradare la qualita'.
- `local` e' un fallback offline utile, ma non produce una traduzione latina completa.
- `--watch` e' pensato per output testuale, non per `--image`.

## Licenza

MIT. Vedi `LICENSE`.
