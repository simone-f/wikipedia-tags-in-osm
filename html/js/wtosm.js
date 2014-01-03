$(document).ready(function() {
        $(".missing_template_alert").click(function (event) {
                event.preventDefault();

                var input = $( this );

                var lat = input.attr( 'data-lat') ;
                var lon = input.attr( 'data-lon' ) ;

                var msg = "All'articolo in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord).";
                    msg += "\n\nAggiungi in cima alla pagina il seguente codice, completando le coordinate:";
                    msg += "\n\n{{coord|" + lat + "|" + lon + "|display=title}}";

                alert(msg);
        });
});