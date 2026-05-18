# televideo-linux

CLI minimale per consultare Rai Televideo dal terminale Linux.

Il progetto nasce per avere un comando rapido, senza browser, per leggere le
pagine testuali di Televideo, visualizzare la pagina grafica originale quando
serve, consultare le ultime notizie RSS e salvare l'output in file di testo.

Mediavideo e' gestito separatamente: il teletext Mediaset e' stato dismesso a
gennaio 2022, quindi non esiste un servizio live ufficiale da interrogare.

## Funzioni

- Consultazione pagine Rai Televideo in solo testo.
- Consultazione pagine regionali Rai, per esempio Lazio o Lombardia.
- Visualizzazione grafica delle pagine PNG con `chafa`.
- Feed Ultim'Ora via RSS con titoli o testo completo.
- Ricerca testuale nel feed Ultim'Ora.
- Riassunto medievale delle notizie con titoli latinizzati.
- Cattura delle sottopagine disponibili per una pagina.
- Refresh automatico stile televideo con `--watch`.
- Salvataggio output testuale con `-o` / `--output`.
- Timeout e retry configurabili.
- Fallback automatico tra `televideo.rai.it` e `servizitelevideo.rai.it`.

## Requisiti

Obbligatorio:

- Python 3.
- Solo standard library Python, nessun pacchetto `pip` richiesto.

Opzionale:

- `chafa`, usato solo per `--image`.

## Installazione Locale

Dal repository:

```sh
chmod +x televideo mediavideo
./televideo 100
```

Installazione come comandi di sistema:

```sh
sudo install -m 755 televideo /usr/local/bin/televideo
sudo install -m 755 mediavideo /usr/local/bin/mediavideo
```

Dopo l'installazione puoi usare:

```sh
televideo 100
mediavideo
```

## Installare Chafa

`chafa` serve solo per vedere le pagine grafiche originali nel terminale.

Debian/Ubuntu:

```sh
sudo apt install chafa
```

Rocky/RHEL compatibili:

```sh
sudo dnf install -y epel-release
sudo dnf install -y chafa
```

Uso:

```sh
./televideo 100 --image
```

Se `chafa` non e' installato, `--image` stampa l'URL PNG della pagina.

## Uso Rapido

Pagina indice nazionale:

```sh
./televideo
./televideo 100
```

Pagina e sottopagina:

```sh
./televideo 101
./televideo 101 -s 1
```

Pagina regionale:

```sh
./televideo 300 -r Lazio
./televideo 401 -r Lombardia
```

Pagina grafica:

```sh
./televideo 100 --image
./televideo 100 --image --url
```

Ultime notizie RSS:

```sh
./televideo --news
./televideo --news 5
./televideo --news 3 --full
```

Ricerca nelle Ultim'Ora:

```sh
./televideo --search Tajani
./televideo --search energia --news 20 --full
```

Riassunto medievale con titoli in latino:

```sh
./televideo --medieval-summary
./televideo --medieval-summary 5
./televideo --medievale 3 --search Papa
```

Cattura sottopagine:

```sh
./televideo 102 --capture
./televideo 300 -r Lazio --capture
```

Refresh automatico:

```sh
./televideo 101 --watch 30
./televideo --news 5 --watch 60
./televideo 101 --watch 10 --count 3
```

Salvataggio output:

```sh
./televideo 101 -o pagina-101.txt
./televideo --news 10 --full -o ultimora.txt
```

Timeout e retry:

```sh
./televideo 101 --timeout 20 --retries 2
```

## Opzioni CLI

```text
page                  pagina Televideo, default 100
-s, --subpage         sottopagina, es. 1
-r, --region          regione Rai, es. Lazio, Lombardia, Emilia-Romagna
--image               mostra la pagina grafica con chafa, se installato
--capture             cattura tutte le sottopagine disponibili della pagina
--news [N]            mostra le ultime N notizie RSS, default 10
--medieval-summary [N]
--medievale [N]       riassume le ultime N notizie in stile medievale con titoli in latino
--full                con --news, mostra anche il testo completo delle notizie
--search TEXT         cerca nel feed Ultim'Ora; da solo implica --news 20
--watch SECONDS       aggiorna l'output ogni N secondi
--count N             numero di aggiornamenti da fare con --watch
-o, --output FILE     salva l'output testuale in un file
--url                 stampa anche l'URL sorgente usato
--timeout SECONDS     timeout per host in secondi, default 10
--retries N           ritentativi dopo il primo giro, default 1
```

`--image`, `--capture`, `--news` e `--medieval-summary` sono modalita
alternative: usane una sola per volta.

La traduzione latina dei titoli usa un dizionario locale ed euristiche semplici:
non richiede servizi esterni e conserva i nomi propri quando non sono traducibili
in modo affidabile.

## Regioni Supportate

Puoi passare il nome della regione con `-r` / `--region`.

Esempi accettati:

```text
Abruzzo, Alto-Adige, Basilicata, Calabria, Campania, Emilia-Romagna,
Friuli Venezia Giulia, Lazio, Liguria, Lombardia, Marche, Molise,
Piemonte, Puglia, Sardegna, Sicilia, Toscana, Trentino, Umbria,
Valle d'Aosta, Veneto
```

Sono accettate anche alcune varianti pratiche, per esempio `emilia`,
`emilia-romagna`, `friuli` e `valle-aosta`.

## Mediavideo

```sh
./mediavideo
./televideo mediavideo
```

Il comando non prova a scaricare dati finti o archivi non ufficiali. Spiega che
Mediavideo non e' piu' disponibile live perche' il servizio teletext Mediaset e'
stato spento nel 2022.

Se in futuro esistesse un archivio pubblico o un endpoint affidabile, lo script
puo' essere esteso senza cambiare l'interfaccia principale.

## Come E' Stato Creato Il Progetto

Il progetto e' stato creato direttamente dentro un container Linux, partendo da
una directory vuota.

Le fasi principali sono state:

1. Analisi degli endpoint pubblici Rai.
2. Implementazione di una CLI Python senza dipendenze esterne.
3. Aggiunta del comando `mediavideo` come wrapper esplicativo.
4. Verifica reale dei comandi nel terminale.
5. Inizializzazione del repository Git e push su GitHub.

Endpoint Rai individuati e usati:

```text
https://www.televideo.rai.it/televideo/pub/solotesto.jsp?pagina=100
https://www.televideo.rai.it/televideo/pub/solotesto.jsp?pagina=101&sottopagina=01
https://www.televideo.rai.it/televideo/pub/tt4web/Nazionale/16_9_page-100.png
https://www.televideo.rai.it/televideo/pub/rss101.xml
https://www.televideo.rai.it/televideo/pub/catturaSottopagine.jsp?pagina=102&regione=
```

Durante lo sviluppo e' emerso che alcuni endpoint Rai possono andare in timeout.
Per questo la CLI non usa un solo host, ma prova sia:

```text
https://www.televideo.rai.it/televideo/pub/
https://www.servizitelevideo.rai.it/televideo/pub/
```

La CLI espone anche `--timeout` e `--retries`, cosi' l'utente puo' adattare il
comando a connessioni lente o a momenti in cui i server Rai rispondono male.

La parte grafica non scarica librerie Python: usa semplicemente il PNG ufficiale
Rai e, se presente, lo passa a `chafa`, un renderer immagini per terminale.

Per Mediavideo e' stata fatta una verifica separata: il servizio live Mediaset
non risulta piu' disponibile dal 2022. Per evitare informazioni fuorvianti, il
progetto dichiara questo limite in modo esplicito.

## Architettura

File principali:

```text
televideo    CLI Python principale
mediavideo   wrapper shell che richiama televideo mediavideo
README.md    documentazione del progetto
LICENSE      licenza MIT
```

Scelte tecniche:

- `argparse` per l'interfaccia CLI.
- `urllib.request` per HTTP/HTTPS senza dipendenze esterne.
- `xml.etree.ElementTree` per leggere il feed RSS.
- Regex mirate per estrarre il blocco `<pre>` dalle pagine solo testo Rai.
- `tempfile` e `subprocess` per passare i PNG temporanei a `chafa`.

## Verifica

Comandi usati durante lo sviluppo:

```sh
python3 -m py_compile televideo
./televideo 100
./televideo 101 --timeout 20 --retries 2
./televideo 300 -r Lazio
./televideo 100 --image --url
./televideo --news 3
./televideo --news 2 --full
./televideo --search Tajani
./televideo --medieval-summary 3
./televideo --medievale 2 --search Papa
./televideo 102 --capture
./mediavideo
```

## Limiti Noti

- Il progetto dipende dagli endpoint pubblici Rai, che non sono API stabili.
- La qualita' di `--image` dipende dal terminale e da `chafa`.
- `--watch` e' pensato per output testuale, non per `--image`.
- Mediavideo non e' consultabile live perche' il servizio e' stato dismesso.

## Licenza

MIT. Vedi `LICENSE`.
