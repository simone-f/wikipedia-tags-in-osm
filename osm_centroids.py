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


import argparse
import os
import pyspatialite
from pyspatialite import dbapi2 as spatialite
from subprocess import Popen, PIPE, call


class OSMcentroids(object):

    def __init__(self, wOSMFile, wOSMdb, args=None):
        self.wOSMFile = wOSMFile
        self.wOSMdb = wOSMdb

        if args is not None:
            self.args = args

            if self.args.drop_database:
                self.drop_database()

            elif self.args.drop_ways_centroids_table:
                self.drop_table('osm_ways_centroids')

            elif self.args.drop_relations_centroids_table:
                self.drop_table('osm_relations_centroids')

            else:
                if self.args.import_data:
                    self.import_data_in_sqlite_db()

                if self.args.ways:
                    self.create_ways_centroids()

                if self.args.relations:
                    self.create_relations_centroids()

    def import_data_in_sqlite_db(self):
        """Import OSM data with Wikipedia tag in a sqlite database to calculate
           centroids
        """

        print "Import dei dati dal file OSM: "
        print self.wOSMFile
        print "nel database Spatialite: "
        print self.wOSMdb
        print

        command = "spatialite_osm_raw -o {wosm_file} -d {wtosm_db}".format(
            wosm_file=self.wOSMFile,
            wtosm_db=self.wOSMdb)
        call(command, shell=True)

        print
        print "Import completato!"

    def _query_wrapper(self, query):
        con = spatialite.connect(self.wOSMdb)

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "Nessuna tabella creata"

        return cur

    def create_ways_centroids(self):
        query = """CREATE TABLE osm_ways_centroids
                   AS SELECT way_id,
                             AsText(Centroid(ST_Collect(Geometry))) as geom
                      FROM osm_way_refs AS w
                      JOIN osm_nodes AS n
                      ON w.node_id = n.node_id
                      GROUP BY way_id
                """

        self._query_wrapper(query)

        con = spatialite.connect(self.wOSMdb)

        query = """SELECT Count(*)
                   FROM osm_ways_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "Creata una tabella con %d righe" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def create_relations_centroids(self):
        con = spatialite.connect(self.wOSMdb)

        query = """CREATE TEMP TABLE osm_relations_centroids_source
                   AS SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN (SELECT way_id, w.node_id, Geometry
                         FROM osm_way_refs AS w
                         JOIN osm_nodes AS n
                         ON w.node_id = n.node_id
                         ) AS nw
                   ON (type = "W" AND rr.ref = nw.way_id)
                """

        self._query_wrapper(query)

        query = """INSERT INTO osm_relations_centroids_source
                   SELECT rel_id, type, ref, Geometry
                   FROM osm_relation_refs AS rr
                   JOIN osm_nodes AS n
                   ON (type = "N" AND rr.ref = n.node_id)
                """
        self._query_wrapper(query)

        query = """CREATE TABLE osm_relations_centroids
                   AS SELECT rel_id,
                             AsText(Centroid(ST_Collect(Geometry))) as geom
                   FROM osm_relations_centroids_source
                   GROUP BY rel_id
                """
        self._query_wrapper(query)

        query = """SELECT Count(*)
                   FROM osm_relations_centroids
                """

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
            num = cur.fetchone()[0]
            print "Creata una tabella con %d righe" % num
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error
            print "Nessuna tabella creata"

    def _get_coords_from_wkt(self, cur):
        centroids = {}
        if cur:
            for obj_id, wkt in cur:
                coords = [float(c)
                          for c in wkt.strip('POINT(').strip(')').split()
                          ]
                coords.reverse()
                centroids[obj_id] = coords

        return centroids

    def get_relations_centroids(self):
        query = """SELECT rel_id, geom
                   FROM osm_relations_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def get_ways_centroids(self):
        query = """SELECT way_id, geom
                   FROM osm_ways_centroids
                """

        cur = self._query_wrapper(query)

        return self._get_coords_from_wkt(cur)

    def drop_table(self, table_name):
        con = spatialite.connect(self.wOSMdb)

        query = "DROP TABLE {}".format(table_name)

        try:
            with con:
                cur = con.cursor()
            cur.execute(query)
        except spatialite.OperationalError as error:
            print "Failed execution of query:\n%s" % query
            print error

    def drop_database(self):
        proc = Popen(["rm", self.wOSMdb], stderr=PIPE)
        status = proc.wait()

        if status == 0:
            print "Rimosso il database {}".format(self.wOSMdb)
        else:
            output = proc.stderr.read()
            print "rm exited with status: {}".format(status)
            print output


def main():
        # Options
        text = 'A partire dal file contenente gli elementi di OSM con il '\
               'tag Wikipedia (creato con osmfilter) ed importa i dati in un '\
               'database SQLite usando Spatialite '\
               '(e in particolare spatialite_osm_raw). '\
               'Quindi crea due tabelle: '\
               '1) osm_ways_centroids '\
               '2) osm_relations_centroids '\
               '- contenenti i centroidi rispettivamente delle way e delle '\
               'relations con un tag Wikipedia.'\
               'Questi dati sono usati nello script principale nella '\
               'creazione delle pagine e in particolare del collegamento a '\
               "Wikipedia per l'inserimento del template {{coord}}"

        parser = argparse.ArgumentParser(description=text)

        parser.add_argument("-d", "--database",
                            help='Nome del database SQLite/Spatialite da '
                                 'creare [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.sqlite]',
                            dest="wOSMdb",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.sqlite"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-f", "--osm_file",
                            help='Nome del file con i dati OSM (creato con '
                                 'osmfilter) [default: '
                                 './data/OSM/Wikipedia-data-in-OSM.osm]',
                            dest="wOSMFile",
                            default=os.path.join("data",
                                                 "OSM",
                                                 "Wikipedia-data-in-OSM.osm"
                                                 ),
                            action="store"
                            )
        parser.add_argument("-i", "--import_data",
                            help="Import data in the Spatialite database",
                            action="store_true"
                            )
        parser.add_argument("-w", "--ways",
                            help="Calculate centroids for ways",
                            action="store_true"
                            )
        parser.add_argument("-r", "--relations",
                            help="Calculate centroids for relations",
                            action="store_true"
                            )
        parser.add_argument("--drop_database",
                            help="Elimina il database",
                            action="store_true")
        parser.add_argument("--drop_ways_centroids_table",
                            help='Elimina dal database la tabella con i '
                                 'centroidi delle ways: '
                                 'osm_ways_centroids',
                            action="store_true")
        parser.add_argument("--drop_relations_centroids_table",
                            help='Elimina dal database la tabella con i '
                                 'centroidi delle relations: '
                                 'osm_relations_centroids',
                            action="store_true")

        args = parser.parse_args()
        print args

        osm = OSMcentroids(args.wOSMFile, args.wOSMdb, args)

if __name__ == '__main__':
    main()
