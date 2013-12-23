$(document).ready(function() {
        $(".missing_template_alert").click(function (event) {
                var msg = "All'articolo in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord).";
                    msg += "\n\nAggiungi in cima alla pagina il seguente codice, completando le coordinate:";
                    msg += "\n\n{{coord|lat (gradi decimali)|N|long (gradi decimali)|E|display=title}}";
                    msg += "\n\nPuoi copiare le coordinate da JOSM: scaricando l\'oggetto e cliccando nel riquadro in basso a sinistra.";
                alert(msg);
        });
});