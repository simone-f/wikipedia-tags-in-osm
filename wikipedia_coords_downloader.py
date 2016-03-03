#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2016 Simone F. <groppo8@gmail.com>
#
#  This file is part of wikipedia-tags-in-osm.
#  wikipedia-tags-in-osm is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  wikipedia-tags-in-osm is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with wikipedia-tags-in-osm.  If not, see <http://www.gnu.org/licenses/>.

"""Download coordinates of Wikipedia articles from MediaWiki API
   https://www.mediawiki.org/wiki/Extension:GeoData#prop.3Dcoordinates
"""

import os
import urllib
import urllib2
import json


class CoordsDownloader:
    def __init__(self, user_agent, coords_file, titles):
        self.user_agent = user_agent
        self.coords_file = coords_file
        self.titles = sorted(titles)
        self.titles_coords, titles_coords_num = self.read_previous_coords()

        titles_to_check = [
            t for t in self.titles if t not in self.titles_coords]

        # with open("titlestodownload", "w") as f:
        #     f.write("\n".join([t.encode("utf-8") for t in titles_to_check]))

        print "Titles:", len(self.titles)
        print "checked in the past: {0}, with coordinates {1}".format(
              len(self.titles_coords), titles_coords_num)

        if len(titles_to_check) == 0:
            print ("The coordinates of all the articles have already been "
                   "downloaded.")
            return

        print "to be checked:", len(titles_to_check)

        # Query Wikpedia for coordinates
        self.query_wikipedia(titles_to_check)

        # Save updated titles' coordinates
        self.save_titles_coords()

    def read_previous_coords(self):
        """Read the titles whose coordinates were downloaded in the past."""
        titles_coords = {}
        titles_coords_num = 0
        if os.path.isfile(self.coords_file):
            lines = [line.rstrip('\n').split("\t")
                     for line in open(self.coords_file)]
            for line in lines:
                title = line[0].decode("utf-8").replace(" ", "_")
                if len(line) == 1:
                    line.append("")
                    line.append("")
                lat = line[1]
                lon = line[2]
                titles_coords[title] = []
                if (lat, lon) != ("", ""):
                    titles_coords_num += 1
                titles_coords[title] = [lat, lon]
        return titles_coords, titles_coords_num

    def query_wikipedia(self, titles_to_check):
        """Query Wikipedia API for coordinates."""
        # Create titles_strings with 50 titles each to query Wikipedia API
        titles_strings = []
        for fifty_titles in [titles_to_check[i:i + 50] for i in range(
                             0, len(titles_to_check), 50)]:
            titles_string = "|".join(fifty_titles)
            titles_strings.append(titles_string)
        print "{0} queries of 50 titles each will be necessay".format(
              len(titles_strings))

        # Download
        print "\n- Download coordinates from Wikipedia"
        for i, titles_string in enumerate(titles_strings):
            continue_string = ""
            cocontinue_string = ""
            print "\nrequest: {0}/{1}".format(i + 1, len(titles_strings))

            # Debugging
            # answer = raw_input("\n  Download 50 titles' coordinates "
            #                    "from Wikipedia?\n  [y/N]")
            answer = "y"
            if answer.lower() != "y":
                print "  Download stopped."
                break

            while True:
                wikipedia_answer = self.download_coordinates(titles_string,
                                                             continue_string,
                                                             cocontinue_string)
                if not wikipedia_answer:
                    break
                # Parsing
                continue_string, cocontinue_string = self.parse_answer()
                if (continue_string, cocontinue_string) == ("", ""):
                    break
                else:
                    print "continue", continue_string, cocontinue_string
            if not wikipedia_answer:
                break

    def download_coordinates(self, titles_string, continue_string,
                             cocontinue_string):
        """Query Wikipedia API for articles' coordinates
        """
        titles = urllib.quote_plus(
            titles_string.replace("_", " ").encode("utf-8"))
        url = ('http://it.wikipedia.org/w/api.php?action=query'
               '&format=json'
               '&titles={0}'
               '&prop=coordinates'
               '&coprimary=primary'
               '&maxlag=5'
               '&continue='.format(titles))
        if continue_string != "":
            url += '{0}&cocontinue={1}'.format(
                       urllib.quote_plus(continue_string),
                       urllib.quote_plus(cocontinue_string))

        request = urllib2.Request(url, None, {'User-Agent': self.user_agent})
        try:
            wikipedia_answer = urllib2.urlopen(request)
        except:
            print ("\n* a problem occurred during download:\n"
                   "{0}, {1}, {2}".format(titles_string.encode("utf-8"),
                                          continue_string.encode("utf-8"),
                                          cocontinue_string.encode("utf-8")))
            return False
        else:
            with open(os.path.join("answer.json"), "w") as f:
                f.write(wikipedia_answer.read())
            return True

    def parse_answer(self):
        """Read coordinates from Wikipedia API answer."""
        with open(os.path.join("answer.json"), "r") as f:
            data = json.load(f)
        for page in data["query"]["pages"].values():
            title = page["title"].replace(" ", "_")
            if title not in self.titles_coords:
                self.titles_coords[title] = ["", ""]
            if "coordinates" in page:
                for coords in page["coordinates"]:
                    self.titles_coords[title] = [coords["lat"], coords["lon"]]
            print "{0}/{1} {2} {3}".format(len(self.titles_coords),
                                           len(self.titles),
                                           title.encode("utf-8"),
                                           self.titles_coords[title])
        if "continue" in data:
            return (data["continue"]["continue"],
                    data["continue"]["cocontinue"])
        else:
            return ("", "")

    def save_titles_coords(self):
        """Save the updated list of articles with coordinates."""
        with open(self.coords_file, "w") as f:
            for i, (title, coordinates) in enumerate(
                    self.titles_coords.iteritems()):
                if len(coordinates) == 2:
                    lat, lon = coordinates
                else:
                    lat, lon = "", ""
                f.write("{0}\t{1}\t{2}".format(title.encode("utf-8"),
                                               lat,
                                               lon))
                if i < len(self.titles_coords) - 1:
                    f.write("\n")


if __name__ == "__main__":
    user_agent = "Some coordinates download test"
    coords_file = "articles_coords_test.csv"
    titles = ["Archivio Storico Capitolino",
              "Biblioteca Universitaria Alessandrina",
              "Biblioteca Vallicelliana",
              "Biblioteca apostolica vaticana",
              "Biblioteca centrale della Facoltà di Architettura",
              "Biblioteca del Ministero degli Affari Esteri",
              "Biblioteca dell'Accademia Nazionale dei Lincei e Corsiniana",
              "Biblioteca dell'Istituto dell'Enciclopedia Italiana",
              "Biblioteca di papa Agapito I",
              "Biblioteca di storia moderna e contemporanea",
              "Biblioteca e museo teatrale del Burcardo",
              "Biblioteca comunale Augusto Tersenghi",
              "Biblioteca Civica Centrale",
              "Biblioteca Nazionale del Club Alpino Italiano",
              "Biblioteca Reale",
              "Biblioteca capitolare (Vercelli)",
              "Biblioteca civica Italo Calvino",
              "Biblioteca civica Luigi Carluccio",
              "Biblioteca internazionale di cinema e fotografia Mario Gromo",
              "Biblioteca della Libera Università di Bolzano"]
    CoordsDownloader(user_agent,
                     coords_file,
                     [t.decode("utf-8") for t in titles])
    print "\nDone."
