#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2013 Simone F. <groppo8@gmail.com>
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

"""Starting from a list of Wikipedia categories written by the user in
   'config.cfg' file, the script:
   - downloads/updates a national OSM data file
   - downloads from (from Quick Intersection) Wikipedia data regarding the selected
     categories (subcategories names and articles titles)
   - creates webpages for showing which articles are already tagged and
     which ones are not.
"""

import argparse
import os
import time
from subprocess import call
import csv
import ConfigParser
import sys
import json

#local imports
from osm_parser import ParseOSMData
import osm_downloader as OSM
from data_manager import Themes, Regions
from users import Users
from webpages_creator import Creator
import wikipedia_downloader
import nuts4nuts_infer


class App:
    def __init__(self):
        #Options
        text = "A partire da una lista di categorie inserite dall'utente nel file 'config.cfg', lo script:\
 scarica/aggiorna i dati OSM nazionali, scarica da Wikipedia i dati sulle categorie (gli articoli che le compongono)\
 e crea delle pagine HTML indicando gli articoli già taggati e da taggare in OSM."
        parser = argparse.ArgumentParser(description=text)
        group = parser.add_mutually_exclusive_group()
        #Manage OSM data
        parser.add_argument("-d", "--download_osm",
                            help="Scarica i dati OSM nazionali (da Geofabrik)",
                            action="store_true")
        parser.add_argument("-u", "--update_osm",
                            help="Aggiorna i dati OSM nazionali scaricati (tramite osmupdate)",
                            action="store_true")
        #Analyze data from Wikipedia and OSM
        parser.add_argument("-a", "--analyze",
                            help="Analizza i dati: Wikipedia (sottocategorie ed articoli delle categorie) ed OSM (tag Wikipedia presenti)",
                            action="store_true")
        parser.add_argument("--category_info",
                            help="Analizza i dati e stampa le informazioni su una specifica categoria",
                            action="store")
        parser.add_argument("-t", "--show_missing_templates",
                            help="Segnala gli articoli senza template Coord",
                            action="store_true")
        parser.add_argument("-c", "--show_link_to_wikipedia_coordinates",
                            help="Se un articolo non taggato ha delle coordinate su Wikipedia, mostra un link per zoomare sulla sua posizione con JOSM",
                            action="store_true")
        parser.add_argument("-o", "--show_coordinates_from_osm",
                            help="Calcola le coordinate del punto (per i nodi) o del centroide (per way e relations) dell'oggetto",
                            action="store_true")
        parser.add_argument("-n", "--infer_coordinates_from_wikipedia",
                            help="Usa Nuts4Nuts per cercare le coordinate di un articolo non taggato e senza coordinate su Wikipedia",
                            action="store_true")
        group.add_argument("-p", "--print_categories_list",
                           help="Analizza i dati e stampa la lista delle categorie nel progetto.",
                           action="store_true")
        #Create webpages
        group.add_argument("-w", "--create_webpages",
                           help="Analizza i dati ed aggiorna le pagine web",
                           action="store_true")
        parser.add_argument("-s", "--save_stats",
                            help="Se sono state aggiornate le pagine web, salva il conteggio aggiornato con il numero di articoli taggati (default: chiedi cosa fare).",
                            action="store_true")
        parser.add_argument("--nofx",
                            help="Non aprire le pagine web in Firefox dopo averle aggiornate.",
                            action="store_true")
        parser.add_argument("--copy",
                            help="Copia la cartella html nella directory descritta nel file config.cfg (es. dir dropbox).",
                            action="store_true")
        self.args = parser.parse_args()
        if self.args.category_info or self.args.category_info\
           or self.args.create_webpages or self.args.print_categories_list\
           or self.args.show_missing_templates\
           or self.args.show_coordinates_from_osm:
            self.args.analyze = True

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)
        os.chdir(os.path.dirname(sys.argv[0]))

        #Configurations
        themesAndCatsNames = self.read_config()

### Manage OpenStreetMap data ##########################################
        #Analyse national OSM data file and create lists of already
        #tagged Wikipedia articles.

        #Download/update OSM data
        if self.args.download_osm or self.args.update_osm:
            if self.args.download_osm:
                OSM.download_osm_data(self)
            if self.args.update_osm:
                status = OSM.update_osm_data(self)
        if self.args.download_osm or (self.args.update_osm and status):
            OSM.filter_wikipedia_data_in_osm_file(self)
        if self.args.update_osm and not status:
            print "I dati OSM erano già aggiornati all'ultimo minuto, o l'aggiornamento con osmupdate è stato interrotto.\
Per ripetere l'aggiornamento, lanciare nuovamente lo script con l'opzione -u."

        if not self.args.analyze:
            #"There's nothing left for me to tell you"
            sys.exit(1)
        else:
            if not os.path.isfile(self.wOSMFile):
                OSM.filter_wikipedia_data_in_osm_file(self)
            #Extract Wikipedia articles tagged in OSM with preferred language.
            #If an article is tagged in a foreign language, ask to Wikpedia
            #what is the corresponding article of the preferred language, so
            #that we can flag it as tagged aswell.
            print "\n- Estrai dal file OSM gli articoli già taggati"
            parseOSMData = ParseOSMData(self)
            #list of Wikipedia tags in OSM
            self.tagsInOSM = parseOSMData.allTags
            self.tagsData = parseOSMData.tagsData
            #list of tagged Wikipedia articles
            self.taggedTitles = parseOSMData.titles
            #tags with errors
            self.wrongTags = parseOSMData.wrongTags
            #ugly tags (with url, language capitalized...), not errors
            self.badTags = parseOSMData.badTags
            #add articles manually flagged as tagged in data/workaround/tagged.csv
            #in case the parser misses them (strange tags)
            self.add_tagged_articles()

            if self.args.show_coordinates_from_osm:
                print "\n--- Aggiungi le coordinate calcolare da OSM"
                parseOSMData.get_centroids()

### Manage Wikipedia data ##############################################
        #Read from 'non-mappable' file the categories and articles that
        #aren't mappable e.g. "Paintings in the X museum",
        #self.nonMappable = {mainCategory.name : {"articles" : [], "subcategories" : []}}
        self.nonMappable = self.read_non_mappable_items()

        #Check if we have Wikipedia data from Quick Intersection of all the
        #categories in the project (config.cfg file)
        themesAndCatsNames = wikipedia_downloader.check_catscan_data(self, themesAndCatsNames)

        #Organize Wikipedia data.
        #self.themes = [Theme(), ...]
        #  Theme().categories = [Category(), ...]
        #    Category().subcategories = [Category(), ...]
        #    Category().articles = [Article(), ...]
        #categories without Quick Intersection data
        self.categoriesWithoutData = []
        allThemes = Themes(self, themesAndCatsNames)
        self.themes = allThemes.themesList

        #Organize data in regions, for a different visualization
        #self.regions = [Region()]
        #  Region().categories = [Category(), ... ]
        self.regions = Regions(self).regionsList

        #Print names of all categories
        if self.args.print_categories_list:
            self.display_categories_names()
            if not self.args.category_info:
                #"There's nothing left for me to tell you"
                sys.exit(1)

### Merge OSM info into Wikipedia data #################################
        #Add to Wikipedia categories and articles istances info about
        #their status in OSM: (tagged/not tagged), osm ids and counters
        print "\n- Controlla quali articoli nelle liste sono già taggati nel file OSM"
        for theme in self.themes:
            for category in theme.categories:
                category.check_articles_in_osm()
        self.titlesInOSM, self.titlesNotInOSM = allThemes.lists_of_titles_in_osm_or_not()

        #Ask to Wikipedia which articles have/have not Coord template.
        #Articles with article.hasTemplate == False will be marked on web pages.
        if self.args.show_missing_templates:
            print "\n- Controlla quali articoli non hanno il template Coord in Wikipedia"
            self.templatesStatus = wikipedia_downloader.read_old_templates_status(self)
            wikipedia_downloader.update_templates_status(self)
            #Set hasTemplate = False to articles without Coord template
            for theme in self.themes:
                for category in theme.categories:
                    category.set_has_template_in_articles()

        #If an article is not already tagged in OSM but Wikipedia knows its
        #position, it is possible to add a link to zoom to that position
        #with JOSM.
        if self.args.show_link_to_wikipedia_coordinates:
            print "\n- Controlla di quali articoli non taggati Wikipedia conosce già la posizione"
            wikipedia_downloader.add_wikipedia_coordinates(self)
            #Save GeoJSON file with titles and coordinates known by Wikipedia
            self.save_titles_with_coords_geojson()

        if self.args.infer_coordinates_from_wikipedia:
            print "\n- Usa Nuts4Nuts per inferire la posizione di alcuni articoli"
            nuts4nuts_infer.infer_coordinates_with_nuts4nuts(self)

        #For debugging
        # print info about a specific category
        if self.args.category_info:
            self.print_category_info(self.args.category_info.replace(" ", "_"))
            if self.args.create_webpages:
                raw_input("\nContinue?[Press any key]")
        # write categories trees to text files (uncomment lines)
        if self.print_categories_to_text_files == "true":
            for theme in self.themes:
                for category in theme.categories:
                    category.print_category_tree_to_file()

        #Read and update stats with the number of tagged articles
        self.dates, self.days = self.read_past_stats()
        download_other_countries = False
        self.todayDate, today = self.read_new_stats(download_other_countries)
        self.days.append(today)
        self.dates.append(self.todayDate)
        if len(self.dates) > 1 and self.todayDate == self.dates[-2]:
                #This is the second analysis of today.
                #Overwrite the previous statistics
                del self.dates[-2]
                del self.days[-2]
                print "\n Questa è la seconda volta che i dati vengono analizzati oggi. \
    Il numero di articoli taggati sostituisce quelli precedenti nella tabella dei conteggi."

        #Count tags added by each user
        self.users = Users(self).users

        #Create a json file with the data (needed by non_mappable.html)
        tree = {"mappable": True,
                "name": "Main",
                "size": 1,
                "children": []}
        for theme in self.themes:
            for category in theme.categories:
                tree["children"].append(category.build_json_tree())
        ifile = open(os.path.join(self.HTMLDIR, "json", "main.json"), "w")
        data = json.dumps(tree)
        ifile.write(data)
        ifile.close()

        #Create webpages
        if self.args.create_webpages:
            print "\n- Crea pagine web"
            Creator(self)

        #Save stats
        if self.args.create_webpages and self.args.save_stats:
            answer = "y"
        else:
            answer = raw_input("\n- Salvo il numero di articoli mappati/da mappare in './data/stats/stats.csv'?\n  [y/N]\n")
        if answer in ("y", "Y"):
            self.save_stats_to_csv()
        else:
            print "\nI nuovi conteggi non vengono salvati."

        #Copy files from html dir to outdir (for example a Dropbox directory)
        if self.args.copy:
            self.copy_html_files_to_outdir()

        print "\nDone."

    def save_titles_with_coords_geojson(self):
        """Save a GeoJSON file with the coordinates known by Wikipedia.
           It is used by the "Map" tab in homepage
        """
        tree = {"type": "FeatureCollection", "features": []}
        i = 0
        for title, coords in self.titlesWithCoordsFromWikipedia.iteritems():
            if title in self.titlesNotInOSM:
                i += 1
                lat, lon = coords
                feature = {"type": "Feature",
                           "properties": {"id": str(i),
                                          "title": title.replace("_", " ").encode("utf-8")
                                         },
                           "geometry": {"type": "Point",
                                        "coordinates": [lon, lat]
                                       }
                          }
                tree["features"].append(feature)
        print "  markers: %d" % len(tree["features"])
        coordsFile = open(os.path.join("html", "GeoJSON", "coords.js"), "w")
        data = json.dumps(tree)
        data = "var coords = %s" % data
        coordsFile.write(data)
        coordsFile.close()

### Configurations #####################################################
    def read_config(self):
        """Setup configurations
        """
        # Program version
        self.version = "v0.3.1.1"

        #Read configuration from config files
        configFile = "config.cfg"
        if not os.path.isfile(configFile):
            call("cp %s %s" % ("config.template", configFile), shell=True)
            print "* A new config file has been created:\n  %s\n\n  Fill it with the necessary information (see README.md and config.template)." % configFile
            answer = raw_input("\n  Continue? [Y/n]\n")
            if answer not in ("", "Y", "y"):
                sys.exit()
        configparser = ConfigParser.RawConfigParser()
        configparser.optionxform = str
        configparser.read(configFile)
        #country
        self.WIKIPEDIALANG = configparser.get("general", "preferred language")
        self.country = configparser.get("general", "country")
        self.OSMDIR = configparser.get("general", "osmdir")
        self.COUNTRYBBOX = configparser.get("general", "osmbbox")
        self.countryPoly = os.path.join("data", "OSM", "%s.poly" % self.country)
        if self.WIKIPEDIALANG == "" or self.country == "" or self.OSMDIR == "":
            print "\n* Inserisci nel file 'config.cfg' le opzioni 'osmdir', 'preferred language', 'country'"
            sys.exit(1)
        # directory where html files must be copied after creation
        #(for example, Dropbox dir)
        self.OUTDIR = configparser.get("general", "outdir")
        #debugging
        self.print_categories_to_text_files = configparser.get("debug", "print categories to text files")
        self.clickable_cells = configparser.get("debug", "clickable cells")
        #themes and categories
        themesAndCatsNames = {}
        for themeName in configparser.options("themes"):
            categoriesNames = [c.strip().replace(" ", "_").decode("utf-8") for c in configparser.get("themes", themeName).split("|")]
            themesAndCatsNames[themeName.replace(" ", "_").decode("utf-8")] = categoriesNames
        # Wikipedia categories data, downloaded from quick_intersection
        self.CATSCANDIR = os.path.join("data", "wikipedia", "catscan")
        self.make_dir(self.CATSCANDIR)
        #categories dates
        self.categoriesDates = {}
        catsDatesFile = os.path.join(self.CATSCANDIR, "update_dates.cfg")
        catsDatesConfigparser = ConfigParser.RawConfigParser()
        catsDatesConfigparser.optionxform = str
        if not os.path.isfile(catsDatesFile):
            catsDatesConfigparser.add_section('catscan dates')
            with open(catsDatesFile, 'wb') as configfile:
                catsDatesConfigparser.write(configfile)
        else:
            catsDatesConfigparser.read(catsDatesFile)
            for categoryName, date in catsDatesConfigparser.items("catscan dates"):
                self.categoriesDates[categoryName] = date

        # OSM data
        self.countryPBF = os.path.join(self.OSMDIR, "%s-latest.osm.pbf" % self.country)
        self.oldCountryPBF = os.path.join(self.OSMDIR, "%s.osm.pbf" % self.country)
        self.countryO5M = os.path.join(self.OSMDIR, "%s-latest.o5m" % self.country)
        self.oldCountryO5M = os.path.join(self.OSMDIR, "%s.o5m" % self.country)
        self.osmObjs = {}
        # OSM data with wikipedia tag
        self.wOSMFile = os.path.join("data", "OSM", "Wikipedia-data-in-OSM.osm")
        # OSM data SQlite database
        self.wOSMdb = os.path.join("data", "OSM", "Wikipedia-data-in-OSM.sqlite")
        # libspatialite path
        self.libspatialitePath = configparser.get("general", "libspatialite-path")
        # OSM data of foreign coountries
        self.FOREIGNOSMDIR = "/tmp/"
        # lists of categories and articles that should be ignored
        # (not geographic content)
        self.NONMAPPABLE = os.path.join("data", "wikipedia", "non_mappable")
        # conversions foreign articles titles - preferred language articles
        self.WIKIPEDIAANSWERS = os.path.join("data", "wikipedia", "answers")
        self.WIKIPEDIAANSWER = os.path.join(self.WIKIPEDIAANSWERS, "answer")
        # web pages dir
        self.HTMLDIR = 'html'
        self.make_dir(os.path.join(self.HTMLDIR, "subpages"))
        self.make_dir(os.path.join(self.HTMLDIR, "GeoJSON"))
        self.make_dir(os.path.join(self.HTMLDIR, "json"))
        self.homePageTitle = "Articoli Wikipedia etichettabili in OSM"
        self.UPDATETIME = time.strftime("%b %d, ore %H", time.localtime())
        # stats and logs dir
        statsDir = os.path.join("data", "stats")
        self.make_dir(statsDir)
        self.make_dir(os.path.join("data", "logs"))
        # templates dir
        self.MISSINGTEMPLATESDIR = os.path.join("data", "wikipedia", "missing_templates")
        self.make_dir(self.MISSINGTEMPLATESDIR)
        self.TEMPLATESSTATUSFILE = os.path.join(self.MISSINGTEMPLATESDIR, "missing_templates.csv")
        return themesAndCatsNames

    def make_dir(self, path):
        """Create a directory if it does not already exist
        """
        if not os.path.exists(path):
            os.makedirs(path)

### Not mappable items and false positive tags #########################
    def read_non_mappable_items(self):
        """Read lists of categories and articles that must be ignored,
           because not mappable.
           Wikipedia articles or categories like: "Paintings in the X museum",
           "Opere nel Castello Sforzesco‎"...
        """
        print "\n- Leggi le liste di articoli e categorie da ignorare perché non mappabili, dal file './data/wikipedia/non_mappable'"
        articles = []
        subcategories = []
        redirects = []
        nonMappable = {"subcategories": subcategories,
                       "articles": articles,
                       "redirects": redirects}
        for itemsType, itemsList in nonMappable.iteritems():
            fileName = open(os.path.join(self.NONMAPPABLE, itemsType), "r")
            nonMappableItems = fileName.read().replace(" ", "_").decode("utf-8").splitlines()
            fileName.close()
            nonMappableItems.sort()
            nonMappable[itemsType] = nonMappableItems

        return nonMappable

    def add_tagged_articles(self):
        """Read from file "./data/workaround/tagged.csv" articles flagged as tagged
           by hand, in case the parser did not detected them.
        """
        ifile = open(os.path.join("data", "workaround", "tagged.csv"), "rb")
        reader = csv.reader(ifile, delimiter='\t')
        for row in reader:
            if row != [] and row[0][0] != "#":
                if len(row) == 2:
                    articleName = row[0].replace(" ", "_")
                    osmIds = row[1].split(",")
                    self.taggedTitles[articleName] = osmIds
        ifile.close()

### Print info to terminal #############################################
    def print_category_info(self, categoryName):
        """Print to the terminal informaions about the reqiested category
        """
        catFound = False
        for theme in self.themes:
            for category in theme.categories:
                if catFound:
                    break
                if category.name == categoryName:
                    category.print_info()
                    catFound = True
                    break
                for subcategory in category.subcategories:
                    if subcategory.name == categoryName:
                        subcategory.print_info()
                        catFound = True
                        break
        if not catFound:
            print "\nNessuna categoria trovata con il nome specificato."

    def display_categories_names(self):
        """Print to terminal the list of main categories
        """
        print "\n=CATEGORIES="
        categoryNum = 0
        for theme in self.themes:
            print "\n%s:" % theme.name
            for category in theme.categories:
                print "%d - %s" % (categoryNum, category.name.replace("_", " "))
                categoryNum += 1

### Statistics #########################################################
    def read_past_stats(self):
        """Read stats
        """
        statsFile = os.path.join("data", "stats", "stats.csv")
        if not os.path.isfile(statsFile):
            dates = []
            days = []
        else:
            ifile = open(statsFile, "r")
            reader = csv.reader(ifile, delimiter='\t', quotechar='"')
            #list with the number of tagged articles, per day
            days = []
            for rowNum, row in enumerate(reader):
                if rowNum == 0:
                    #date
                    dates = row[1:]
                    for date in dates:
                        days.append({})
                else:
                    #data
                    status = row[0]
                    for dateIndex, value in enumerate(row[1:]):
                        if value == "":
                            days[dateIndex][status] = ""
                        else:
                            days[dateIndex][status] = int(value)
            ifile.close()
        return dates, days

    def count_wkp_tags_in_file(self, country):
        """Count the number of 'wikipedia=*' in OSM file
        """
        print "\n conteggio del numero di tag wikipedia tags"
        if country == "italy":
            path = self.OSMDIR
        else:
            path = "/tmp/"
        call('osmfilter %s%s.o5m --out-count | grep wikipedia > data/stats/%s' % (path, country, country), shell=True)
        file_in = open("data/%s" % country, "r")
        lines = file_in.readlines()
        file_in.close()
        tagsInCountry = 0
        for line in lines:
            line = line.replace(" ", "")[:-1]
            tagsInCountry += int(line.split("\t")[0])
        return tagsInCountry

    def read_new_stats(self, download_other_countries):
        """Add latest numbers to stats
        """
        todayDate = self.UPDATETIME.split(",")[0]
        today = {"to do": len(self.titlesNotInOSM),
                 "mapped": len(self.titlesInOSM),
                 "total": len(self.tagsInOSM)}
        #Print tags numbers of other countries
        if download_other_countries:
            print "\n- Tags numbers in countries (with duplicate articles"
            tagsNum = {"italy": self.tagsInOSM, "spain": "", "france": "", "germany": ""}
            for country in tagsNum:
                print "\n- %s:" % country
                if self.country != "italy":
                    #download other countries
                    print "\n downloading..."
                    url = "http://download.geofabrik.de/osm/europe/%s.osm.pbf" % country
                    call('wget -c %s -O %s.osm.pbf' % (url, country), shell=True)
                    print "\n converting to 05m..."
                    call('osmconvert %s.osm.pbf -o=%s.o5m' % (country, country), shell=True)
                    call('rm %s.osm.pbf' % (country), shell=True)
                    #count tags "wikipedia=*"
                    tagsInCountry = self.count_wkp_tags_in_file(country)
                    tagsNum[country] = tagsInCountry
                print country, tagsNum[country]
        return todayDate, today

    def save_stats_to_csv(self):
        """Save stats to file
        """
        print "\n- Salvataggio dei dati su file CSV"
        statsDir = os.path.join("data", "stats")
        statsFile = os.path.join(statsDir, "stats.csv")
        oldStatsFile = os.path.join(statsDir, "old_stats.csv")
        if os.path.isfile(oldStatsFile):
            call('mv %s %s' % (statsFile, oldStatsFile), shell=True)
        ofile = open(statsFile, "w")
        writer = csv.writer(ofile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)
        #headers
        header = [" "] + [date for date in self.dates]
        writer.writerow(header)
        #days that must be saved to CSV file
        daysToSave = self.days
        #data
        for status in self.days[0]:
            values = [status] + [day[status] for day in daysToSave]
            writer.writerow(values)
        ofile.close()

### Copy webpages to a second directory ################################
    def copy_html_files_to_outdir(self):
        """Copy html files to another directory, for example Dropbox dir
        """
        print "\n- Copia i file delle pagine web nella directory '%s'" % self.OUTDIR
        if self.OUTDIR == "":
            print "\n  *Scrivi nel file 'config.cfg' --> 'outdir', il path della directory su cui copiare i file."
        else:
            call("cp -R ./html/* %s" % self.OUTDIR, shell=True)


def main():
    App()

if __name__ == '__main__':
    main()
