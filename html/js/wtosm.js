function pad (n, width, z) {
  z = z || '0';
  n = n + '';
  return n.length >= width ? n : new Array(width - n.length + 1).join(z) + n;
}

function deg2dms (dd) {
    var tmp_dd = dd;

    if ( dd < 0 ) {
        tmp_dd = -dd;
    }

    mnt = Math.floor (tmp_dd*3600/60);
    sec = Math.round ( (tmp_dd*3600 % 60) * 100) / 100;

    deg = Math.floor(mnt / 60);
    mnt = mnt % 60;

    var dms = {'d': pad(deg, 2, 0),
               'm': pad(mnt, 2, 0),
               's': sec
               }

    return dms;
}


function coords_deg2dms_cp (lat, lon) {
    var lat_cp = 'N';
    var lon_cp = 'E';

    if (lat >= 0.0) {
        lat_cp = 'N';
    }
    else {
        lat_cp = 'S';
    }

    if (lon >= 0.0) {
        lon_cp = 'E';
    }
    else {
        lon_cp = 'W';
    }

    var lat_dms = deg2dms(lat);
    var lon_dms = deg2dms(lon);

    lat_dms['cp'] = lat_cp;
    lon_dms['cp'] = lon_cp;

    var dms = {'lat': lat_dms,
               'lon': lon_dms
               };

    return dms;
}

$(document).ready(function () {
        $(".missing_template_alert").click(function (event) {
                event.preventDefault();

                var input = $( this );

                var lat = input.attr( 'data-lat');
                var lon = input.attr( 'data-lon' );
                var dim = input.attr( 'data-dim' );

                var res = coords_deg2dms_cp(lat, lon);

                var msg = "Alla voce in Wikipedia manca il testo per mostrare le coordinate e la mappa OSM (il template Coord)."
                    msg += "\n\nAggiungi in cima alla pagina il seguente codice:";

                var tmpl_lat = res.lat.d + "|" + res.lat.m + "|" + res.lat.s + "|" + res.lat.cp;
                var tmpl_lon = res.lon.d + "|" + res.lon.m + "|" + res.lon.s + "|" + res.lon.cp;

                var tmpl_dim = '';

                    if ( dim > 0 ) {
                        tmpl_dim = "|dim:" + dim;
                    }

                    msg += "\n\n{{coord|" + tmpl_lat + "|" + tmpl_lon + tmpl_dim + "|display=title}}";

                alert(msg);
        });
});