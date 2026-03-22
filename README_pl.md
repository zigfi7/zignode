🔌 Zignode – ultraszybki, samoodkrywający się system RPC dla Pythona (i nie tylko)

Masz dość pisania dedykowanych serwerów za każdym razem, gdy chcesz sterować urządzeniem przez sieć? Zignode to lekkie narzędzie, które zamienia dowolny skrypt Pythona w inteligentny, sieciowy węzeł — często wystarczy jeden import i jedna linijka kodu.

Zapomnij o konfiguracji czy obsłudze żądań HTTP. Wystarczy udostępnić funkcje, a Zignode zrobi resztę: węzły automatycznie się odnajdują, dzielą zdolnościami i współpracują przy zdalnych wywołaniach funkcji w sieci LAN. To zdecentralizowany system RPC, który po prostu działa.
🧭 Filozofia KISS: prostota, która działa

Zignode powstał z potrzeby połączenia potęgi elektroniki niskopoziomowej z wygodą sterowania sieciowego — bez zbędnej komplikacji. Zgodnie z zasadą KISS (Keep It Simple, Stupid), narzędzie nie wchodzi w drogę i pozwala skupić się na tym, co najważniejsze.

    Dla hobbystów: steruj Raspberry Pi, ESP32 czy robotami z dowolnego komputera w sieci — bez pisania serwera.

    Dla programistów i testerów: buduj zdecentralizowane środowiska testowe i rozdzielaj zadania bez centralnego brokera.

    Dla każdego: twórz samoorganizującą się sieć inteligentnych urządzeń, które po prostu się komunikują.

✨ Idealne zastosowania

    Automatyka domowa: skrypt na laptopie wywołuje turn_on_lights() na Raspberry Pi w innym pokoju.

    Robotyka i elektronika: główna jednostka robota deleguje read_distance() czy set_motor_speed() do mikrokontrolerów.

    Testy automatyczne: uruchamiaj testy na wielu platformach (Linux, Windows, mobile) wywołując funkcje na zdalnych węzłach.

    Prosty computing rozproszony: rozdzielaj zadania (np. przetwarzanie obrazów, walidacja danych) po sieci LAN.

🚀 Główne cechy

    ⚙️ Błyskawiczna integracja: wystarczy zignode.auto(locals()) na końcu skryptu Pythona i już jesteś online.

    🌐 Automatyczne odkrywanie: węzły skanują sieć i odnajdują się same. Bez konfiguracji, serwera centralnego czy plików.

    🧠 Zdecentralizowane trasowanie: Zignode buduje "umysł siatki" i przekazuje zlecenia do odpowiednich węzłów, nawet przez innych sąsiadów (routing 2-hop).

    🎯 Elastyczne wywołania: wspiera argumenty pozycyjne (args), nazwane (kwargs), celowanie po ID lub przez wyszukiwanie zdolności.

    🖥️ Wieloplatformowość: działa na systemach Linux, Windows i macOS bez dodatkowej konfiguracji.

    🦦 Lekki i interoperacyjny: oparty na asyncio i aiohttp, używa standardowego HTTP/JSON. Protokół jest kompatybilny z ESP32, MicroPythonem i Arduino.

    🔍 Konfigurowalne skanowanie:

        full: skanowanie całych podsieci.

        basic: skanowanie tylko zdefiniowanej listy adresów.

        disabled: tryb pasywny, bez skanowania.
        Manualna lista adresów akceptuje hostname, IPv4, IPv6 oraz niestandardowe porty.

    🐞 Tryb debugowania: szczegółowe logowanie skanów, komunikatów sieciowych i wewnętrznych zdarzeń węzłów.

    🔖 Własna nazwa węzła: opcjonalny parametr name, np. zignode.auto(locals(), name="cmd_zignode").

⚙️ Jak to działa?

Zignode tworzy sieć peer-to-peer, gdzie wszystkie węzły są równe:

    Start: Węzeł uruchamia lekki serwer aiohttp i (w zależności od trybu) skanuje sieć lokalną na porcie 8635.

    Odkrywanie: Po znalezieniu sąsiadów wymienia się z nimi listą swoich funkcji oraz listą znanych mu sąsiadów. Proces jest powtarzany cyklicznie, co czyni sieć samonaprawiającą się.

    Wykonanie:

        Funkcja jest lokalna? → jest wykonywana od razu.

        Nie ma jej lokalnie? → węzeł pyta bezpośrednich sąsiadów.

        Nadal brak? → pyta sąsiadów, czy ich sąsiedzi posiadają funkcję (routing 2-hop).

        Po znalezieniu, wynik wraca do nadawcy tą samą drogą.

        Jeśli funkcja nie zostanie odnaleziona w sieci, zwracany jest błąd.

Efekt: niezawodna, siatkowa sieć RPC bez pojedynczego punktu awarii.

W aktualnych wdrożeniach Zignode pełni też rolę control-plane dla dynamicznych wysp logicznych: fizyczny graf node'ów może się zmieniać, ale logiczna grupa funkcji pozostaje stabilna i może być używana przez wyższe warstwy orkiestracji, takie jak Ziginput.
📦 Instalacja i użycie

Wymagania: Python 3.8+

pip install zignode

Przykład (moje_urzadzenie.py):

#!/usr/bin/python
# -*- coding: utf-8 -*-
import zignode

def ustaw_serwo(pozycja: int, predkosc: int = 100):
    print(f"SERWO: Przesuwam do pozycji {pozycja} stopni z prędkością {predkosc}.")
    return f"OK: Ustawiono pozycję serwa na {pozycja}."

def odczytaj_temperature():
    temp = 23.5
    print(f"CZUJNIK: Odczytano temperaturę: {temp}C")
    return {"temperatura": temp, "jednostka": "Celsius"}

if __name__ == '__main__':
    zignode.auto(
        external_locals=locals(),
        debug=True
    )

Uruchom i gotowe:

python moje_urzadzenie.py

📬 Wywoływanie funkcji

Możesz używać dowolnego klienta HTTP (curl, requests, Postman):

1. Argumenty pozycyjne (args):

curl -X POST -H "Content-Type: application/json" \
-d '{"call": "ustaw_serwo", "args": [90]}' \
http://localhost:8635/

2. Argumenty nazwane (kwargs):

curl -X POST -H "Content-Type: application/json" \
-d '{"call": "ustaw_serwo", "kwargs": {"pozycja": 180, "predkosc": 50}}' \
http://localhost:8635/

🌐 Ekosystem i Integracje

    Interfejs Webowy: Każdy węzeł udostępnia prosty panel WWW pod adresem http://<ip>:8635/ z listą funkcji, sąsiadów i statusem. Dzięki obsłudze CORS, można łatwo tworzyć aplikacje webowe komunikujące się z siecią Zignode.

    Klient HTML: W repozytorium znajduje się gotowy klient HTML, który po podłączeniu do dowolnego aktywnego węzła wyświetla interaktywną mapę sieci i pozwala na wywoływanie funkcji na dowolnym urządzeniu.

    Wersja lite: Dostępna jest synchroniczna wersja zignode-lite, która nie wymaga żadnych zewnętrznych zależności (poza standardową dystrybucją Pythona). Działa w trybie pasywnym i jest idealna dla prostych zastosowań.

    Implementacja Arduino: Istnieje również implementacja na Wemos D1 (ESP8266) z obsługą WiFi i wyświetlacza. Działa jako pasywny węzeł, zdolny do wykonywania poleceń.

    Praktyczne wdrożenie: Projekt został przetestowany w praktyce na Raspberry Pi sterującym 16 serwomechanizmami (PCA9685), z dedykowanym interfejsem webowym do kontroli w czasie rzeczywistym przez sieć Zignode.

🚧 Plan rozwoju
🧱 Najbliższe plany i rozważania:

    Implementacja WebSockets: Dla zwiększenia responsywności sieci i umożliwienia aktywnego przesyłania zdarzeń (push).

    Warstwa bezpieczeństwa (opcjonalna): Mechanizmy (np. tokeny) do zabezpieczenia sieci przed nieautoryzowanym dostępem. Kluczowe dla zastosowań komercyjnych lub w sieciach publicznych.

    Timery i zadania w tle: Możliwość uruchamiania długotrwałych zadań bez blokowania węzła, z opcją startu i zatrzymania.

    Wsparcie dla MQTT: Rozważana implementacja jako dodatkowej, opcjonalnej metody komunikacji.

🌌 Wizja długoterminowa:

    Pamięć rozproszona: Mechanizmy współdzielenia stanu i danych między węzłami.

    Bogatsza orkiestracja wysp: dynamiczne wyspy logiczne są już używane; kolejnym krokiem jest głębsze planowanie, rozmieszczanie i koordynacja gridu nad istniejącym modelem wysp.

    Abstrakcyjne warstwy logiczne: Możliwość budowania bardziej skomplikowanych, wielopoziomowych systemów.

    Protokoły bezpośrednie: Implementacja niesieciowych metod komunikacji (np. przez porty szeregowe) do sterowania rojami robotów.

🧑‍💻 Historia Zignode

Zignode nie powstał w oderwaniu od rzeczywistości. To efekt lat pracy z elektroniką, robotyką i automatyzacją testów. Wszystko zaczęło się od frustracji: sterowanie sprzętem to frajda, ale pisanie do tego celu w kółko tych samych warstw sieciowych? Męczące.

Pomyślałem: dlaczego nie mogę po prostu wywołać funkcji na innym urządzeniu tak, jak robię to lokalnie?

Dlatego stworzyłem system, który jest:

    Zdecentralizowany (bez pojedynczego punktu awarii)

    Samoorganizujący się (zero konfiguracji)

    Intuicyjny (działa od razu)

Zignode to narzędzie, które szanuje Twój czas i upraszcza systemy rozproszone.
👥 Autorzy i podziękowania

    Pomysł, architektura, implementacja: Zigfi

    Protokół: zaprojektowany tak, by był czytelny dla człowieka i niezależny językowo.

    Wsparcie AI: z pomocą modeli od Google, OpenAI, Anthropic i innych.

Każdy feedback, fork i PR jest mile widziany!
📜 Licencja

Projekt na licencji Apache 2.0. Szczegóły w pliku LICENSE.
