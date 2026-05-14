FINANCIAL ASSISTANT — Portable Build
====================================

Indítás
-------
  Dupla katt: RUN.bat   (vagy a Start menü "Financial Assistant" ikonjára)
  Egy böngészőablak nyílik a http://localhost:8000 címmel.
  Az app 1 órányi tétlenség után automatikusan leáll — a következő indítás
  pár másodperc alatt újra elindítja.

Leállítás (ha nem akarod megvárni az auto-leállást)
---------------------------------------------------
  Dupla katt: STOP.bat   (vagy Start menü "Stop Financial Assistant")

Hova kerül az adatod
--------------------
  %APPDATA%\FinancialAssistant\financial.db
  (Az újratelepítés vagy frissítés nem törli — biztonságos backup-olni
  innen, ha akarsz.)

Ha SmartScreen figyelmeztet az installer-re ("Windows protected your PC")
------------------------------------------------------------------------
  Az installer nincs aláírva (egy magánfejlesztő csomagja).
  Kattints: "More info" → "Run anyway".
  Ez egyszeri lépés.

Probléma esetén
---------------
  A naplófájlok itt találhatók:
    <install_dir>\app-scripts\uvicorn-stderr.log
    <install_dir>\app-scripts\start-error.log
    <install_dir>\app-scripts\stop.log
  Küldd el ezeket annak akitől a programot kaptad.

Forrás
------
  https://github.com/Donuttouchme/Financial_Assistant