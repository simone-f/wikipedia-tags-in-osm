#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Fondazione Bruno Kessler
#  Author: <consonni@fbk.eu>
#  This work has been funded by Fondazione Bruano Kessler (Trento, Italy)
#  under projects T2DataExchange and LOD4STAT
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.
#  If not, see <http://www.gnu.org/licenses/>.


def coords_deg2dms_cp(lat, lon):
    if lat >= 0.0:
        lat_cp = 'N'
    else:
        lat_cp = 'S'

    if lon >= 0.0:
        lon_cp = 'E'
    else:
        lon_cp = 'W'

    lat_dms = deg2dms(lat)
    lon_dms = deg2dms(lon)

    fields = ('d', 'm', 's', 'cp')
    lat_res = dict(zip(fields, lat_dms + tuple(lat_cp)))
    lon_res = dict(zip(fields, lon_dms + tuple(lon_cp)))

    return {'lat': lat_res, 'lon': lon_res}


def format_dms(dms):
    return {'lat': {'d': int(round(dms['lat']['d'])),
                    'm': int(round(dms['lat']['m'])),
                    's': int(round(dms['lat']['s'])),
                    'cp': dms['lat']['cp']
                    },
            'lon': {'d': int(round(dms['lon']['d'])),
                    'm': int(round(dms['lon']['m'])),
                    's': int(round(dms['lon']['s'])),
                    'cp': dms['lon']['cp']
                    }
            }


def dms2str(dms):
    dmsf = format_dms(dms)
    return "{lat_d:02d}°{lat_m:02d}'{lat_s:02d}\"{lat_cp} "\
           "{lon_d:02d}°{lon_m:02d}'{lon_s:02d}\"{lon_cp}"\
           .format(lat_d=dmsf['lat']['d'],
                   lat_m=dmsf['lat']['m'],
                   lat_s=dmsf['lat']['s'],
                   lat_cp=dmsf['lat']['cp'],
                   lon_d=dmsf['lon']['d'],
                   lon_m=dmsf['lon']['m'],
                   lon_s=dmsf['lon']['s'],
                   lon_cp=dmsf['lon']['cp']
                   )


def deg2dms(dd):
    if dd < 0:
        dd = -dd

    mnt, sec = divmod(dd*3600, 60)
    deg, mnt = divmod(mnt, 60)
    return deg, mnt, sec


if __name__ == '__main__':
    print
    print 'Coordinate di Berlino'
    print 'deg: (52.518611, 13.408056)'
    dms = coords_deg2dms_cp(52.518611, 13.408056)
    dms_str = dms2str(dms)
    print 'dms: ', dms_str
    print 'atteso: 52°31\'07"N 13°24\'29"E'
    print format_dms(dms)
    print
    print 'Coordinate di Washington D.C.'
    print 'deg: (38.895111, -77.036667)'
    dms = coords_deg2dms_cp(38.895111, -77.036667)
    dms_str = dms2str(dms)
    print 'dms: ', dms_str
    print 'atteso: 38°53\'42"N 77°02\'12"W'
    print format_dms(dms)
    print
    print 'Coordinate di Santiago del Cile'
    print 'deg: (-33.437833, -70.650333)'
    dms = coords_deg2dms_cp(-33.437833, -70.650333)
    dms_str = dms2str(dms)
    print 'dms: ', dms_str
    print 'atteso: 33°26\'16"S 70°39\'01"W'
    print format_dms(dms)
