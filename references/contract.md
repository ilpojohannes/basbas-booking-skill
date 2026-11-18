# Sopimus ja turvallisuusrajat

Nykyinen adapteri tunnistaa vain moduulin `mod_0VWSE3bovStZfY` ja ravintolan `res_0VWSAUspRta7lU`. Yksin nimen osuma ei riitä: welcome-tekstin pitää tunnistaa Bistro sisäpihalla. Legacy TableOnline ei kuulu tähän ajuriin.

Julkiset UI-luennat on kokeiltu kirjoitukset estettynä. Tällä versiolla paikalliset provider-fixturet kattavat kalenterin, saatavuuden, tyhjät lisätuotteet/promootiot, yhden tarkasti rajatun varaus-POSTin ja tarkan read-backin. Kaikki muut API-pyynnöt estetään mockissa; commitissa vain yksi tarkastettu POST sallitaan. POSTin edellä luodaan atominen pysyvä yritystiedosto ja hyväksyntä merkitään käytetyksi. Verkkovirhe ei poista niitä.

Aikojen käyttäjäranking voittaa palvelimen järjestyksen. Waitlist-only, muu alue tai promootio ei kelpaa. Vahvistuksen UTC-aika verrataan Helsinki-aikaan aikavyöhyketietoisesti. Pelkkä HTTP 2xx, klikkaus tai pending ei ole vahvistus.

Mock-fixture on skeeman perusteella laadittu synteettinen testidata. Oikeita käyttöehto- tai tietosuojadokumentteja ei jaeta mukana. Lyhyt paikan tunnistuslause ja julkiset ID:t ovat adapterin välttämättömiä tunnisteita. Testiehdot eivät koskaan kelpaa live-hyväksynnäksi.

Huomautuskenttä on provider-konfiguraation kenttälistassa, mutta havaitussa nykyisessä Details-UI:ssa sitä ei renderöidä. Tästä syystä ei-tyhjä huomautus on aina `note_field_unknown`-este jo ennen selainta tai yhteystietoja. Rajoitus kerrotaan heti keskustelun alussa, ennen yhteystietojen pyytämistä tai ajastusta; käyttäjä ohjataan tekemään huomautusta tarvitseva varaus itse. Allergioita ei saa jättää pois automatisoinnin mahdollistamiseksi. V1:n maksu-/guarantee-tuki on tarkoituksella nolla.

Selaimen ulkopuolinen suora API GET voi palauttaa 403, vaikka kirjoitukset estetty selain toimii. Älä päättele palvelun olevan alhaalla tämän perusteella äläkä kierrä estettä kirjoituskutsuilla.

Ajastimen sovitin on protokolla. Fake-host-testi todistaa hyväksyntävaatimuksen ja read-back-vertailun, ei minkään tuotantoajastimen käyttöönottoa. Aidon ajastuksen todentaminen kuuluu agentin operaattorivirtaan ja edellyttää lupaa.
