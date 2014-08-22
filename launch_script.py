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
import locale
from subprocess import call
import csv
import ConfigParser
import sys
import json
import webbrowser
from babel.support import Translations

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
        text = """Starting from a list of Wikipedia categories written by the user in
'config.cfg' file, the script:
- downloads/updates a national OSM data file
- downloads from (from Quick Intersection) Wikipedia data regarding the selected
 categories (subcategories and articles names)
- creates webpages for showing which articles are already tagged and
 which ones are not.
"""
        parser = argparse.ArgumentParser(description=text)
        group = parser.add_mutually_exclusive_group()
        #Manage OSM data
        parser.add_argument("-d", "--download_osm",
                            help="Download OSM data of the country (from Geofabrik)",
                            action="store_true")
        parser.add_argument("-u", "--update_osm",
                            help="Update downloaded OSM data of the country (through osmupdate)",
                            action="store_true")
        #Analyze data from Wikipedia and OSM
        parser.add_argument("-a", "--analyze",
                            help="Analyze Wikipedia data (categories' sub-categories and articles) ed OSM data (existing Wikipedia tags)",
                            action="store_true")
        parser.add_argument("--category_info",
                            help="Analyze data and print informations regarding a specific category",
                            action="store")
        parser.add_argument("-t", "--show_missing_templates",
                            help="Mark on web pages the articles that miss geo template (Coord)",
                            action="store_true")
        parser.add_argument("-c", "--show_link_to_wikipedia_coordinates",
                            help="If a non-tagged article have the coordinates on Wikipedia, show on the web pages a link to zoom on its position with JOSM/iD",
                            action="store_true")
        parser.add_argument("-o", "--show_coordinates_from_osm",
                            help="Calculate OSM coordinates of articles (point for nodes, centroids for ways and relations)",
                            action="store_true")
        parser.add_argument("-n", "--infer_coordinates_from_wikipedia",
                            help="Use Nuts4Nuts to calculate the coordinates of a non tagged article whithout coordinates on Wikipedia",
                            action="store_true")
        group.add_argument("-p", "--print_categories_list",
                           help="Analyze data and print project's categories.",
                           action="store_true")
        #Create webpages
        group.add_argument("-w", "--create_webpages",
                           help="Analyze data and create web pages",
                           action="store_true")
        parser.add_argument("-s", "--save_stats",
                            help="If web pages have been created, store the updated number of tagged articles (default: ask to user).",
                            action="store_true")
        parser.add_argument("--fx",
                            help="Open the web pages with the system browser after creation.",
                            action="store_true")
        parser.add_argument("--copy",
                            help="Copy html folder to the directory configured on `config.cfg` (eg. dropbox dir).",
                            action="store_true")
        parser.add_argument("--locale",
                            nargs='+',
                            dest='locales',
                            metavar='LANG',
                            help="Generate pages in the specified locales. Default: use the system locale. ")

        self.args = parser.parse_args()
        if self.args.category_info or self.args.category_info\
           or self.args.create_webpages or self.args.print_categories_list\
           or self.args.show_missing_templates\
           or self.args.show_coordinates_from_osm:
            self.args.analyze = True

        # Default value for locale
        # get system locale
        sys_locale_langcode, sys_locale_encoding = locale.getdefaultlocale()

        if not self.args.locales:
            self.args.locales = [sys_locale_langcode]

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
            print "OSM data where already uptodate or osmupdate has been interrupted.\
To repeat the updating process, launch the script again with the `-u` option."

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
            print "\n- Read from OSM file the already tagged articles"
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
                print "\n--- Add OSM coordinates to the articles"
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
        print "\n- Check which articles are already tagged in country's OSM file"
        for theme in self.themes:
            for category in theme.categories:
                category.check_articles_in_osm()
        self.titlesInOSM, self.titlesNotInOSM = allThemes.lists_of_titles_in_osm_or_not()

        #Ask to Wikipedia which articles have/have not Coord template.
        #Articles with article.hasTemplate == False will be marked on web pages.
        if self.args.show_missing_templates:
            print "\n- Check which articles miss geo template (Coord) in Wikipedia"
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
            print "\n- Check the non tagged articles whose position is known by Wikipedia"
            wikipedia_downloader.add_wikipedia_coordinates(self)
            #Save GeoJSON file with titles and coordinates known by Wikipedia
            self.save_titles_with_coords_geojson()

        if self.args.infer_coordinates_from_wikipedia:
            print "\n- Use Nuts4Nuts to infer coordinates of non tagged articles, whose position is unknown by Wikipedia"
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
                print "\n This is the second time that data ara analyzed today. \
The number of tagged articles will replace that of the lust run in the tags' numbers table."

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
            # Restrict to the supported locales
            self.locales = frozenset(self.SUPPORTED_LOCALES).intersection(
                frozenset(self.args.locales))

            non_supported_locales = frozenset(self.args.locales) - \
                                        frozenset(self.SUPPORTED_LOCALES)

            for locale_langcode in non_supported_locales:
                print 'Warning: dropping unsupported locale: {0}'.format(
                       locale_langcode)

            # if no supported locale is chosen fallback to en_US
            if not self.locales:
                self.locales = frozenset(['en_US'])

            for locale_langcode in self.locales:
                self.translations = Translations.load("locale",
                                                      [locale_langcode]
                                                      )
                self._ = self.translations.ugettext
                print "\n- Create web pages with locale: ", locale_langcode
                Creator(self, locale_langcode)

                if self.args.fx:
                    url = os.path.join('html', locale_langcode, 'index.html')
                    # using .get() suppress stdout output from browser, won't
                    # suppress stderr
                    webbrowser.get().open_new(url)

            #Save stats
            if self.args.save_stats:
                self.save_stats_to_csv()
                print "\nNew stats have been saved."
            else:
                print "\nNo stats saved."

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
        if not os.path.isfile(self.countryPoly):
            print "\n* Poly file is missing: \n  %s" % self.countryPoly
            sys.exit(1)
        if self.WIKIPEDIALANG == "" or self.country == "" or self.OSMDIR == "":
            print "\n* Fill in `config.cfg` file the following options: `osmdir`, `preferred language`, `country`"
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

        supported_locales = configparser.get("i18n", "supported_locales")
        self.SUPPORTED_LOCALES = [lcode.strip()
                                  for lcode in supported_locales.split('|')
                                  ]

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
        print "\n- Read the lists of articles and categories which must be ignored because flagged as non-mappable from the files in `./data/wikipedia/non_mappable`"
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
            print "\nNo categories found with the specified name."

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
        print "\n number of wikipedia tags"
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
                    print "\n converting to O5M..."
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
        print "\n- Saving stats to CSV file"
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
        print "\n- Copy files from `html` dir to: '%s'" % self.OUTDIR
        if self.OUTDIR == "":
            print "\n  *Write in `config.cfg` --> `outdir` teh path of the directory in which you want to copy the files."
        else:
            call("cp -R ./html/* %s" % self.OUTDIR, shell=True)


def main():
    App()

if __name__ == '__main__':
    main()
