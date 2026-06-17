# Testa Reseappen – steg för steg

Appen körs på din **dator** (servern), men du testar den i **mobilens
webbläsare**. Telefonen och datorn måste vara på **samma wifi**.

## 1. Hämta filerna till din dator

Packa upp reseapp_med_git_historik.tar.gz (skickad i chatten) någonstans
på din dator, t.ex. Skrivbord\reseapp. Eller använd filerna som redan
ligger i Google Drive (My Drive > Appar > IWST > reseapp) — ladda ner hela
mappen.

## 2. Installera Python (om du inte redan har det)

Windows: gå till https://python.org/downloads, ladda ner senaste
versionen, kör installern. Kryssa i "Add python.exe to PATH" i
installationsguiden — annars hittar inte kommandoraden Python.

Kontrollera att det fungerade: öppna Kommandotolken (sök "cmd" i
Startmenyn) och skriv:
  python --version
Du ska se något i stil med "Python 3.12.x".

## 3. Installera appens beroenden

I Kommandotolken, navigera till mappen där du packade upp projektet:
  cd Skrivbord\reseapp
  pip install -r requirements.txt
Detta installerar Flask och requests — de två bibliotek appen behöver.

## 4. Starta servern

Fortfarande i samma Kommandotolk-fönster:
  python app.py
Du ska se text som slutar med något i stil med:
  * Running on http://127.0.0.1:5000
  * Running on http://192.168.1.23:5000

Den ANDRA raden (192.168.x.x) är datorns adress på ditt wifi-nätverk —
den behöver du i nästa steg. Lämna detta fönster öppet — stänger du det
stängs servern.

Om du inte ser en sådan rad: öppna ett nytt Kommandotolk-fönster och skriv
"ipconfig", leta efter "IPv4-adress" under ditt wifi-nätverkskort.

## 5. Öppna appen i mobilen

1. Anslut mobilen till samma wifi som datorn.
2. Öppna mobilens webbläsare (Chrome/Safari).
3. Skriv adressen från steg 4, t.ex: http://192.168.1.23:5000
   (byt ut mot din egen IP-adress, och glöm inte :5000 på slutet).
4. Sidan "Vad finns nära oss?" ska laddas.

## 6. Testa funktionerna

1. Skriv ditt namn i fältet.
2. Tryck "Hitta platser nära mig".
3. Mobilen frågar om lov att dela din position — tryck Tillåt.
4. Appen listar platser i närheten (utsikt, historiskt, bad, restaurang)
   hämtat live från OpenStreetMap.
5. Tryck 👍 eller 👎 på en plats — siffran ska uppdateras direkt.
6. Be en familjemedlem öppna samma adress i sin mobil (samma wifi) och
   rösta också — ni delar samma databas (samma dator = samma server).

## Vanliga problem

"Den här sidan kan inte nås" i mobilen
→ Kolla att mobilen och datorn verkligen är på samma wifi (inte t.ex.
mobilt 4G/5G på telefonen). Kolla att IP-adressen och porten (:5000)
stavades rätt.

Inga platser hittas
→ Du måste faktiskt vara utomhus/nära riktiga platser för att GPS + OSM-data
ska ge resultat. Testa hemma också, men förvänta dig färre/inga träffar
beroende på vad som finns registrerat i OpenStreetMap där du är.

Datorn går i viloläge / stänger av wifi
→ Stäng av automatisk viloläge på datorn under resan när du vill att
appen ska vara tillgänglig, annars stängs servern ner.

## Senare (frivilligt): köra på riktig server

Just nu kräver appen att din dator är igång och att alla är på samma
wifi. Om du vill kunna nås även utanför hemmanätet (t.ex. om ni delar
upp er under en utflykt) behövs ett enkelt moln-hosting-steg — säg till
om du vill bygga det som nästa version.
