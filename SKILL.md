---
name: basbas-booking-public
description: "Use when booking the original BasBas Bistro safely."
version: 1.0.0
---

# Pöytä BasBasiin. Ei taikatemppuja.

Vain alkuperäinen Baskeri & Basso Bistro Tehtaankadun sisäpihalla. Ei Kulmaa, Studiota, jonotuslistaa, puhelua tai muuta ravintolaa ilman erillistä lupaa.
Virallinen sivu https://basbas.fi/bistro/ ja sen varauslinkki. Nykyinen moduuli https://book.tableonline.com/mod_0VWSE3bovStZfY?lang=en .

## 1. Kysy puuttuvat asiat, älä täytä niitä itse

- Ruokailupäivä **vuosineen** tai paremmuusjärjestykseen laitetut vaihtoehtoiset päivät. Tarkista päivämäärän viikonpäivä ohjelmallisesti ja kerro ristiriidasta. Älä muuta päivää hiljaa.
- Henkilömäärä. Tarkista nykyisestä live-käyttöliittymästä tuettu määrä (v1 hyväksyy 1–7, ei tarkoita että pöytiä löytyy).
- Ovatko kellonajat **täsmällinen paremmuusjärjestys** (esim. 18, 19, 17) vai **jatkuva aikaväli**, jonka sisällä muita aloitusaikoja saa valita? Diskreettiin listaan ei saa keksiä väliaikoja. Aikavälille kysy ihanneaika ja tasatilanteen järjestys; muodosta vasta sitten eksplisiittinen `slot_preferences`.
- Erityisruokavaliot, allergiat ja huomautus, myös vastaus ”ei”. V1 ei lähetä huomautuksia: ei-tyhjä `note` on ennen kirjoitusta pysäyttävä manuaalisen varauksen este, ei syy jättää allergiaa pois.
- Varaajan yhteystiedot paikallisesta käyttäjän hyväksymästä lähteestä. Ei salasanoja tai yhteystietoja chattiin. Erillinen omistettu 0600 JSON, ei agentin globaalia ympäristöä.

Kysy erillisenä, vapaaehtoisena asiana täsmälleen:
> Haluatko, että tarkistan varausvahvistuksen myös sähköpostistasi, jos sähköpostiyhteys on käytettävissä?

Sähköposti ei ole edellytys varaukselle. `email_check_opt_in=false` oletuksena. Myöntävä vastaus koskee vain tämän varauksen vahvistusviestiä; ei yleistä postilaatikon tutkimista. Selvitä käytössä oleva sähköpostityökalu ja sen käyttöoikeudet, älä pyydä salasanaa chattiin. Paketissa ei ole sähköpostiasiakasta. Sähköpostin tarkistuslupa ei ole markkinointilupa.

## 2. Selvitä kyvykkyydet ennen lupausta

Lue README ja aja `python scripts/setup_check.py`. Se kokeilee oikeaa paikallista selainta, ei asenna mitään. Puuttuva Playwright/Chromium on este: selitä asennus ja mahdolliset kulut ja pyydä lupa, älä asenna automaattisesti. Hostin `crontab`/`systemctl`/`hermes` löytyminen ei todista ajastimen toimintaa. Selvitä agentin kestävät ajastustyökalut, niiden tila, aikavyöhyke, aikakatkaisut ja tuloksen palautuskanava. Chat ei herää itsestään. Jos kestävää ajastusta ei ole, sano se ja tarjoa käyttäjän käynnistämää ajoa.

Hermesissä käytä saatavilla olevan cron-työkalun skeemaa, älä arvaa komentoparametreja, chat-ID:tä tai toimituskohdetta. Listaa ennen luontia, päivitä saman tehtävän olemassa oleva ajastus. Luo/muuta vasta käyttäjän hyväksynnällä. Lue ajastus takaisin ja varmista absoluuttinen suoritushetki Helsinki-ajassa, vain yksi kampanja, kertaluonteisuus, sallittu aikaraja ja toimituskohde. `scripts/host_adapter.py` määrittelee testatun neutraalin `capabilities/create_once/read`-sopimuksen; se ei itse koske hostiin.

## 3. Näytä yhteenveto ja hanki ennakkovaltuutus

Yhteenveto: Bistro, tarkat päivät ja niiden järjestys, henkilömäärä, kellonaikojen semantiikka ja järjestys, huomautus, markkinointi pois, hyväksyttävät nykyiset ehdot ja rajatut yritysikkunat Helsinki-ajassa. Erota ruokailupäivä, arvioitu vapautumispäivä ja havaittu vapautumishetki. Tavallinen 30 päivän raja on tarkistettava live-moduulin `last_bookable_date`-arvosta, ei lupaus tulevasta varastosta.

Pyydä yksiselitteinen lupa: ”Saanko varata tämän yhteenvedon mukaisen ensimmäisen sallitun pöydän näissä aikarajoissa ilman uutta kysymystä?” Täsmällinen ennakkovaltuutus riittää vapautumishetkellä. Tallenna hyväksyntä erilliseen 0600 tiedostoon vasta vastauksen jälkeen. Se sisältää kampanjan kaikki kentät, täsmällisen paikan ja live-ehtojen sormenjäljen. Älä luo hyväksyntää mallipohjan `approved=false` vaihtamiseksi omin päin.

Uusi maksu, ennakkomaksu, korttitakuu, no-show/peruutusmaksu, minimikulutus, olennainen ehtomuutos, CAPTCHA tai 3-D Secure: **pysähdy ja pyydä uusi päätös**. V1 ei tue maksuvelvoitteita edes yleisellä varausluvalla. Älä muuta ehtohashia vain saadaksesi testit läpi.

## 4. Turvallinen valmistelu ja ajo

Kopioi esimerkkikonfiguraatio yksityiseen hakemistoon, muuta arvot sovittuun mandaattiin. Tiedostot 0600, hakemistot 0700. Polut ovat käyttäjän valitsemia. Tila on `$BASBAS_STATE_DIR` tai `$XDG_STATE_HOME/basbas-booking-public` (oletus `~/.local/state`). Ei tuotantokampanjoiden tilan lukua tai kopiointia.

1. `python scripts/cli.py validate --config CONFIG`
2. `python -m unittest discover -s tests -v` ja `python tests/browser_flows.py -v`.
3. Päivänä ennen **vapautumista**, ei ruokailua: `python scripts/cli.py previous-day --config CONFIG`. Tämä yhdistää kirjoitukset estetyn live-yhteensopivuustarkistuksen ja paikallisesti interceptoidut success/fallback/pending/canceled-harjoitukset. Vapautumaton tavoite ei ole virhe yhteensopivuustestissä, mutta ei myöskään näyttö tarjolla olevasta pöydästä. Viimeisin epäonnistuminen korvaa aiemman onnistumisen.
4. Vapautumishetkellä `python scripts/cli.py release-rehearsal --config CONFIG`: kaikki palveluntarjoajan kirjoitukset estetty, yhteystietoja ei lueta eikä syötetä. Commit edellyttää alle 5 minuuttia vanhaa `dry-run-ready`-tulosta sekä edellisen päivän `compatibility-ready`-tulosta täsmälleen samalle konfiguraatiolle.
5. Vain hyväksytyssä ikkunassa, oikeilla aiemmilla tuloksilla ja käyttäjän luvalla: `python scripts/runner.py --config CONFIG --mode commit --approval-file APPROVAL --contact-file CONTACT`. **Tätä komentoa ei ajeta asennus- tai jakelutestinä.** Kontaktikenttien täyttäminen voi jo itsessään tehdä varauksen; kirjoitusportti ja yritysmerkintä on siksi aseistettu ennen syöttöä.

Runner käyttää nykyisen UI:n havaittua yhtä POST-sopimusta, ei legacy-API:a. Tuore selain tarkistaa moduulin, ravintolan, Bistro-tervehdyksen, päivän, henkilöt, ajat, ehdot ja rahaehdot uudelleen. Service workerit ja WebSocketit estetään. Markkinointi pysyy pois. Tuntemattomat pyynnöt, lisätuotteet tai vastaustilat pysäyttävät.

V1:n runner käsittelee yhtä päivää per konfiguraatio. Agentti käsittelee hyväksytyt päivät järjestyksessä. Seuraavaan päivään saa edetä vain varmistetusti **ennen kirjoitusta** syntyneestä puuttuvan saatavuuden tuloksesta; ei aikakatkaisun/virheen perusteella. Eri päiville omat konfiguraatiot ja täsmälliset hyväksynnät, mutta **sama `campaign_id` kaikille yhden varausmandaatin vaihtoehtopäiville**. Tämä sitoo yhden atomisen yritysmerkinnän koko mandaattiin: kirjoituksen alettua myös muut päivät lukittuvat. Harjoitustulokset erotellaan kampanjan sisällä päivittäin. Säilytä sama sovittu päivien järjestys ihmisen yhteenvedossa. Ei rinnakkaisia commit-ajoja. Päiväjärjestyksen orkestrointi ei ole automaattinen host-ajastin tässä paketissa.

## 5. Päättele lopputulos varovasti

Ainoa success: exact read-back samasta booking ID:stä, oikeat moduuli- ja ravintola-ID:t, päivä, henkilömäärä ja Helsinki-aika, `reserved`/`confirmed`, `state.current` sama, `ttl=null`, puuttuvat kentät/promootiot täsmälleen tyhjiä, nollamaksut ja ei takuuta. UTC pitää muuntaa Europe/Helsinkiin, ei käyttää aina +02. Tarkista näkyvä vahvistus kun saatavilla; sen puute raportoidaan varoituksena. Vapaaehtoinen sähköposti voi vahvistaa vain tämän varauksen, jos lupa ja yhteys ovat olemassa.

Pending, canceled tai epäselvä vastaus ei ole onnistuminen. Kun kirjoitus on alkanut, yritys on pysyvästi terminaalinen, myös verkkovirheessä. Älä poista merkintää, varaa vaihtoehtoa tai yritä uudelleen. Sovita olemassa oleva varaus vain tarkalla read-backilla tai käyttäjän sallimalla vahvistusviestillä. Älä peru tai tee siivouskirjoitusta omin päin.

`python scripts/cli.py report --config CONFIG` tekee rajatun raportin ilman yhteystietoja tai reusable tokeneita. Ilmoita suomeksi täsmällinen päivä, Helsinki-kellonaika, henkilöt ja vahvistettu/epäselvä/estynyt tila; booking ID voidaan kertoa yksityisessä kanavassa, ei julkisessa jakelussa. Älä julkaise tosielämän varausdataa.

Uudelleenyrittämistä vain ennen ensimmäistä kirjoitusta, vain käyttäjän erikseen hyväksymissä `windows`-ikkunoissa. Älä jatka yön yli tai aamulle ilman täsmällistä erillistä lupaa. Teknistä UI-korjausta saa tehdä vain säilyttäen turvaportit ja ajamalla regressiot sekä tuore read-only rehearsal uudelleen. V1 ei sisällä automaattista korjaussupervisoria. Saatavuutta, tarkkaa vapautumisaikaa tai onnistumista ei voi luvata 100 %.
