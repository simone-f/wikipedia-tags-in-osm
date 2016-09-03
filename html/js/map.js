var osmLayer = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
});

var map = L.map('map', {
    center: [42.391, 13.118],
    zoom: 6
}).addLayer(osmLayer);

var markers = new L.MarkerClusterGroup({disableClusteringAtZoom: 12,
                                        maxClusterRadius : 60});
var geoJsonLayer = L.geoJson(coords, {
    onEachFeature: function (feature, layer) {
        // Label
        layer.bindLabel(feature.properties.title);
        // Popup
        var articleLink = "<a href=\"http://it.wikipedia.org/wiki/" + encodeURI(feature.properties.title) + "\"";
        articleLink += "title=\"Vedi articolo su Wikipedia\" target='_blank'>" + feature.properties.title + "</a>";
        var x = feature.geometry.coordinates[0];
        var y = feature.geometry.coordinates[1];
        var left = x - 0.0005;
        var right = x + 0.0005;
        var top = y + 0.0005;
        var bottom = y - 0.0005;
        var josmUrl = "http://localhost:8111/";
        josmUrl += "load_and_zoom?left=" + left + "&right=" + right + "&top=" + top + "&bottom=" + bottom;
        var josmLink = "\n<a href='" + josmUrl + "' target='_blank' title=\"Zooma in JOSM vicino all'oggetto da taggare\"><img class='articleLinkImg' src='../img/josm_load_and_zoom.png'></a>";
        var idUrl = "http://www.openstreetmap.org/edit?editor=id#map=17/" + y + "/" + x + ""
        var idLink = "\n<a href='" + idUrl + "' target='_blank' title=\"Zooma in iD vicino all'oggetto da taggare\"><img class='articleLinkImg' src='../img/id.png'></a>";
        var tag = "<i>wikipedia=it:" + feature.properties.title + "</i>";
        var text = "\n<table class='popup'>";
        text += "\n  <tr>";
        text += "\n    <td>" + articleLink + "</td>";
        text += "\n  </tr>";
        text += "\n  <tr>";
        text += "\n    <td>Aggiungi il tag:</td>";
        text += "\n  </tr>";
        text += "\n  <tr>";
        text += "\n    <td>" + tag + " <img src=\"../img/copy.svg\" class='copyImg' onClick=\"copyToClipboard('it:" + feature.properties.title.replace("'", "\\'") + "')\" title=\"Copia\"></td>";
        text += "\n  </tr>";
        text += "\n  <tr>";
        text += "\n    <td>" + josmLink + idLink + "</td>";
        text += "\n  </tr>";
        text += "\n</table>";
        layer.bindPopup(text);
    }
});
markers.addLayer(geoJsonLayer);
map.addLayer(markers);

// Copy tag value to clipboard
function copyToClipboard(text) {
    window.prompt("Copia negli appunti: Ctrl+C, Invio", text);
}
