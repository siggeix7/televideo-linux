# Televideo Da Terminale

Utility minimale per consultare Rai Televideo da terminale Linux.

Mediavideo non e' disponibile come servizio live: Mediaset ha dismesso il teletext a gennaio 2022, quindi il comando dedicato mostra un avviso invece di fingere una consultazione non aggiornata.

## Uso

```sh
./televideo
./televideo 101
./televideo 101 -s 1
./televideo 300 -r Lazio
./televideo 100 --url
./televideo 101 --timeout 20 --retries 2
```

Per la pagina grafica, installa opzionalmente `chafa`.

Debian/Ubuntu:

```sh
sudo apt install chafa
```

Rocky/RHEL compatibili:

```sh
sudo dnf install -y epel-release
sudo dnf install -y chafa
```

Poi esegui:

```sh
./televideo 100 --image
```

Senza `chafa`, `--image` stampa l'URL PNG della pagina.

La CLI usa due host Rai (`televideo.rai.it` e `servizitelevideo.rai.it`) e ritenta automaticamente in caso di timeout. Se la tua connessione o il server Rai sono lenti, aumenta `--timeout`.

## Mediavideo

```sh
./mediavideo
./televideo mediavideo
```

Entrambi i comandi spiegano che Mediavideo non e' piu' consultabile live.

## Installazione Di Sistema

```sh
chmod +x televideo mediavideo
sudo install -m 755 televideo /usr/local/bin/televideo
sudo install -m 755 mediavideo /usr/local/bin/mediavideo
```

Dipendenze obbligatorie: solo Python 3 standard library.
