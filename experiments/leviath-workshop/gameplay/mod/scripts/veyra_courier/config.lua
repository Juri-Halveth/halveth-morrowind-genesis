-- SPDX-License-Identifier: MIT
-- This isolated candidate seeds ONE synthetic parcel, not a visitor connection.
return {
    version = 1,
    seedId = 'SYNTHETIC_FIRST_PARCEL',
    courierName = 'Elyra, Botin zwischen den Welten',
    courierTemplate = 'eldafire',
    departureDays = 2,
    cellsPerDay = 10,
    origin = {x=-2, y=-9},
    giftRecordId = 'daedric longsword',
    giftCount = 1,
    letterTitle = 'Ein Brief von jenseits der Welt',
    letterText = '<DIV ALIGN="CENTER">Ein Gruss von jenseits deiner Welt</DIV><BR><BR>'
        ..'Dieses Paket ist der erste technische Probebrief. Es kam im verborgenen Depot an, '
        ..'wartete zwei Spieltage und wurde dann zu dir getragen.<BR><BR>'
        ..'Die Klinge ist ein echtes Morrowind-Item. Diesen Brief und die Klinge darfst du '
        ..'in diesem eigenen Kandidaten-Spielstand behalten.<BR><BR>'
        ..'Absender: synthetischer Werkstatt-Gast<BR>Deine Weltenbotin Elyra',
}
