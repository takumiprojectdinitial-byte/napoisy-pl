# Napisy PL — aplikacja Windows

Aplikacja desktopowa do rozpoznawania mowy w filmach, automatycznego wykrywania języka i tworzenia polskich napisów SRT. Opcjonalnie może utworzyć film MP4 z napisami wtopionymi w obraz.

## Funkcje

- Graficzny interfejs po polsku.
- Automatyczne wykrywanie języka przez Whisper.
- Modele `tiny`, `base`, `small`, `medium`, `large-v3`.
- Zapis napisów jako plik `.pl.srt`.
- Opcjonalne wtopienie napisów do filmu przez FFmpeg.
- Log błędów w `%USERPROFILE%\NapisyPL_error.log`.

## Wymagania

- Windows 10/11 64-bit.
- Python 3.10 lub nowszy do uruchomienia ze źródeł.
- Internet do pobrania modelu przy pierwszym uruchomieniu i do tłumaczenia przez Google Translate.
- FFmpeg tylko wtedy, gdy chcesz wtopić napisy w obraz.
- Przy większych modelach przydaje się więcej RAM; `small` to dobry punkt startowy.

## Uruchomienie ze źródeł

1. Zainstaluj Pythona z https://www.python.org/downloads/ i zaznacz opcję `Add Python to PATH`.
2. Kliknij dwukrotnie `INSTALL_AND_RUN.bat`.
3. W oknie aplikacji wybierz film i kliknij `Generuj polskie napisy`.

Możesz też uruchomić w terminalu:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python napisy_pl.py
```

## Budowanie programu EXE

Na Windows, po instalacji Pythona:

1. Uruchom `BUILD_EXE.bat`.
2. Po zakończeniu aplikacja będzie w `dist\NapisyPL\NapisyPL.exe`.

Budowanie w trybie `onedir` jest celowe: modele AI i biblioteki natywne bywają duże, a ten wariant jest łatwiejszy w diagnozowaniu niż pojedynczy EXE. Folder `dist\NapisyPL` należy przenosić jako całość.

## FFmpeg

Pobierz kompilację dla Windows z linków wymienionych na oficjalnej stronie: https://ffmpeg.org/download.html . Dodaj folder zawierający `ffmpeg.exe` do zmiennej środowiskowej `PATH`, a następnie uruchom aplikację ponownie.

## Prywatność i ograniczenia

- Analiza mowy jest wykonywana lokalnie przez faster-whisper.
- Rozpoznany tekst jest wysyłany do usługi tłumaczącej Google Translate przez `deep-translator`; tłumaczenie wymaga internetu.
- To narzędzie nie jest profesjonalnym edytorem napisów. Wyniki zależą od jakości dźwięku, akcentów, nakładania się głosów i tłumaczenia maszynowego.
- Nie omija DRM ani zabezpieczeń dostępu do filmów.
- Przed publikacją lub rozpowszechnianiem napisów upewnij się, że masz odpowiednie prawa.

## Rozwiązywanie problemów

- `No module named ...`: uruchom `INSTALL_AND_RUN.bat`.
- Pierwsze uruchomienie jest długie: Whisper pobiera model.
- Błąd CUDA: ustaw urządzenie `cpu`.
- Wtapianie napisów nie działa: sprawdź, czy FFmpeg jest w `PATH`; szczegóły błędu będą pokazane w oknie.
- Brak lub złe napisy: spróbuj modelu `medium` albo `large-v3` i sprawdź jakość ścieżki audio.


## Uzyskanie gotowej aplikacji bez instalowania Pythona na swoim komputerze

Repozytorium można zbudować na serwerze Windows przez GitHub Actions. Python jest instalowany wyłącznie na serwerze budującym, nie na komputerze, na którym później uruchamiasz program.

1. Zaloguj się lub załóż konto na https://github.com/.
2. Utwórz nowe repozytorium i wgraj zawartość tego folderu (w tym ukryty folder `.github/workflows`).
3. Otwórz zakładkę **Actions** i wybierz workflow **Build Napisy PL for Windows**.
4. Kliknij **Run workflow** i poczekaj, aż zadanie zakończy się na zielono.
5. Otwórz zakończone zadanie i pobierz artefakt `NapisyPL-Windows-x64`.
6. Rozpakuj ZIP. Uruchom `NapisyPL.exe` z rozpakowanego folderu. Zachowaj cały folder aplikacji, nie kopiuj samego EXE.

Pierwsze uruchomienie programu pobierze model rozpoznawania mowy. Tłumaczenie wymaga połączenia z internetem. Jeśli Windows SmartScreen ostrzeże o nieznanej aplikacji, nie ignoruj ostrzeżenia bez upewnienia się, że pobrałeś plik z własnego zadania budowania.
