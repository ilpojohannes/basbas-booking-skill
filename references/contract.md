# Sopimus ja turvallisuusrajat

Nykyinen adapteri tunnistaa vain moduulin `mod_0VWSE3bovStZfY` ja ravintolan `res_0VWSAUspRta7lU`. Yksin nimen osuma ei riitä: welcome-tekstin pitää tunnistaa Bistro sisäpihalla. Legacy TableOnline ei kuulu tähän ajuriin.

Julkiset UI-luennat on kokeiltu kirjoitukset estettynä. Tällä versiolla paikalliset provider-fixturet kattavat kalenterin, saatavuuden, tyhjät lisätuotteet/promootiot, yhden tarkasti rajatun varaus-POSTin ja tarkan read-backin. Kaikki muut API-pyynnöt estetään mockissa; commitissa vain yksi tarkastettu POST sallitaan. POSTin edellä luodaan atominen pysyvä yritystiedosto ja hyväksyntä merkitään käytetyksi. Verkkovirhe ei poista niitä.

Aikojen käyttäjäranking voittaa palvelimen järjestyksen. Waitlist-only, muu alue tai promootio ei kelpaa. Vahvistuksen UTC-aika verrataan Helsinki-aikaan aikavyöhyketietoisesti. Pelkkä HTTP 2xx, klikkaus tai pending ei ole vahvistus.

Mock-fixture on skeeman perusteella laadittu synteettinen testidata. Oikeita käyttöehto- tai tietosuojadokumentteja ei jaeta mukana. Lyhyt paikan tunnistuslause ja julkiset ID:t ovat adapterin välttämättömiä tunnisteita. Testiehdot eivät koskaan kelpaa live-hyväksynnäksi.

## Huomautuksen sopimus

Havaitussa julkisessa UI:ssa `textarea#note` paljastuu vasta pakollisten yhteystietojen täytyttyä. Sen `maxlength` on 2000 ja placeholder ”Any special requests or dietary requirements?”. Havaittu POST on `/restaurant/res_0VWSAUspRta7lU/book?lang=en`, huomautus täsmälleen `customer.note`-kentässä. Live-havainnon kaikki kirjoitukset estettiin: palvelinpersistenssiä ei väitetä todennetuksi.

- `note` on merkkijono: tyhjä tarkoittaa ei huomautusta; pelkkä whitespace hylätään. HTML-raja lasketaan UTF-16-koodiyksiköissä. Hyväksyttyä tekstiä ei normalisoida. Nykyinen UI trimmaa reunavälit lähetyksessä: tällainen ero estetään `write_note_mismatch`-syyllä, ei korjata hyväksyntää hiljaa.
- Koko konfiguraation `scope_hash` ja hyväksynnän täsmällinen kenttävertailu sitovat myös huomautuksen. Muutos edellyttää uutta hyväksyntää ja harjoituksia.
- Asenna verkkokirjoitusportti ennen kontakteja. Pidä ehdot pois päältä, täytä kontaktit, odota kenttää ja tarkista pituusraja, täytä ja vertaa tarkkaa arvoa. Aseista lähetys vasta tämän jälkeen. Puuttuva/muuttunut kenttä pysäyttää. Aikainen POST estetään paikallisesti, koko ajo päättyy ennen kirjoitusta, eikä yritysmerkintää kuluteta: mitään ei lähetetty palvelimelle.
- Viimeinen kirjoitusportti tarkistaa kaikki aiemmat raha-/ehto-/scope-/kontaktirajat sekä täsmällisen `customer.note`-arvon ennen atomista yritysmerkintää. Vain yksi hyväksytty POST; torjuttua varhaista pyyntöä ei toisteta.
- Mock ja commit vaativat saman huomautuksen read-backista. Puuttuva/eri huomautus kirjoituksen jälkeen on terminaalinen `submitted-or-ambiguous`, `note_delivery=unverified`, ei lupa uuteen yritykseen. Raportoi erikseen huomautuksen todentamatta jääminen. Mock ilmoittaa vain `verified-mock-readback`, oikea read-back `verified-provider-readback`; kumpikaan ei todista ravintolan hyväksyvän ruokavaliopyyntöä.
- Ei huomautuksen raakatekstiä raportteihin, virheisiin, HTML-dumpeihin tai diagnostiikkaan. Yksityinen hyväksytty konfiguraatio on tiedon lähde. Allergioita ei saa jättää pois automatisoinnin vuoksi. Maksu-/guarantee-tuki on edelleen nolla.

`tests/browser_flows.py` ajaa todellisen julkisen UI:n paikallisilla provider-vastauksilla: täsmällinen monirivinen huomautus ja ei-huomautusta-polku (yksi hyväksytty POST), vaarallinen kontaktien automaattilähetys, puuttuva/väärä lähtevä teksti sekä puuttuva/väärä read-back. Se tarkistaa myös diagnostiikan yksityisyyden. Testi ei tee oikeaa varausta.

Selaimen ulkopuolinen suora API GET voi palauttaa 403, vaikka kirjoitukset estetty selain toimii. Älä päättele palvelun olevan alhaalla tämän perusteella äläkä kierrä estettä kirjoituskutsuilla.

Ajastimen sovitin on protokolla. Fake-host-testi todistaa hyväksyntävaatimuksen ja read-back-vertailun, ei minkään tuotantoajastimen käyttöönottoa. Aidon ajastuksen todentaminen kuuluu agentin operaattorivirtaan ja edellyttää lupaa.
