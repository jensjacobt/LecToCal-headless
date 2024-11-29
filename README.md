# LecToCal-headless

LecToCal-headless (nedefor blot LecToCal) er et Python 3 modul til synkronisering af dele af Lectio-kalenderen til Google Kalender.

Ved at bruge Google Kalender, kan du få: notifikationer, deling, adgang fra de fleste devices, integration med andre tjenester så som [If This Then That](https://ifttt.com).

LecToCal-headless er en videreudvikling af [LecToCal](https://github.com/Hanse00/LecToCal). Den største ændring er, at LecToCal-headless bruger Chrome eller Firefox til at hente kalenderbegivenheder fra Lectio, så de kan synkroniseres til Google Kalender. Det gøres uden at browservinduet vises, hvilket kaldes headless på engelsk.

**Bemærk**: Dette program har ingen tilknytning til Lectio eller MaCom (der udvikler og driver Lectio).

## Installation

1. Download en zip-fil med kildekoden fra Releases til højre. 
2. Udpak alle filerne til en mappe. 
3. Åbn mappen i en terminal, og kør `python setup.py install`

## Brug

### Afhængigheder

Du skal have installeret Mozilla Firefox eller Google Chrome for at bruge dette program. (Hvis du vil bruge programmet på Raspberry Pi, så se afsnittet om dette nedenfor.)

### Kørsel

Efter installation, som forklaret ovenfor, kan modulet køres i terminalen som:

```
lectocal
```

### Parametre

For at se alle de påkrævede og valgfrie parametre, kan du køre modulet med `-h` eller `--help` som parameter.

### Eksempel på anvendelse

1. Synkronisér kalenderen ved at køre `lectocal`.

    Ved første kørsel ledes du igennem et forløb, hvor LecToCal gives tilladelse til at foretage ændringer i Google Kalender (så der kan oprettes en kalender, som standard "Lectio", og tilføjes begivenheder fra Lectio til denne kalender). Dette gemmer en fil, så der ikke skal gives tilladelse igen næste gang LecToCal køres.

1. Gentag.

    For at holde kalenderen opdateret, skal punkt 1 gentages jævnligt.

**Bemærk**

Den genererede kalender i Google Kalender bør ikke slettes eller omdøbes, da det kan føre til problemer så som ekstra kopier af kalenderen (da LecToCal opretter en kalender, som standard "Lectio", hvis den ikke findes).

### Raspberry Pi

På vej!

## Udvikling

Så du vil gerne arbejde med koden? Sejt!

Du kan med fordel køre med et virtuelt miljø for ikke at forstyrre dine andre pakkeinstallationer:

1. `python -m venv .venv`
2. `source ./.venv/bin/activate` (eller tilsvarende - se [how venvs work](https://docs.python.org/3/library/venv.html#how-venvs-work))

Derefter installeres de påkrævede pakker:

3. `python setup.py egg_info`
4. `pip install -r lectocal_headless.egg-info/requires.txt`
5. `rm -rf lectocal_headless.egg-info/`
6. `pip install importlib-metadata`

Du skulle nu være klar til at gå i gang.

Hvis du støder på problemer under arbejde på projektet, så er du velkommen til at [oprette et "issue" på GitHub](https://github.com/jensjacobt/LecToCal/issues).

(Det overvejes at skifte til brug af poetry for at forenkle håndteringen af pakker mv.)

## Bugs, feedback, tanker, etc.

Brug endelig [GitHub's issue tracker](https://github.com/jensjacobt/LecToCal/issues). Send evt. en pull request.


## Licens

LecToCal har en Apache 2.0 licens, se [LICENSE](LICENSE) eller apache.org for detajler.
