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

"""Classes for themes, regions and Wikipedia categories and articles
"""

import os
from copy import deepcopy
import operator
import urllib


class Themes:
    def __init__(self, app, themesAndCatsNames):
        self.themesList = []
        for themeId, themeName in enumerate(sorted(themesAndCatsNames.keys())):
            categoriesNames = sorted(themesAndCatsNames[themeName])
            self.themesList.append(Theme(app, themeId, themeName, categoriesNames))

    def lists_of_titles_in_osm_or_not(self):
        """Create two lists with the titles of tagged / non tagged
           articles, to count their numbers
        """
        titlesInOSM = []
        titlesNotInOSM = []
        for theme in self.themesList:
            theme.check_articles_in_osm()
            for title in theme.titlesNotInOSM:
                titlesNotInOSM.append(title)
            for title in theme.titlesInOSM:
                titlesInOSM.append(title)
        titlesInOSM = list(set(titlesInOSM))
        titlesNotInOSM = list(set(titlesNotInOSM))
        return titlesInOSM, titlesNotInOSM


class Theme:
    def __init__(self, app, themeId, name, categoriesNames):
        self.name = name.capitalize()
        self.categories = []
        for catIdx, categoryName in enumerate(categoriesNames):
            catId = "%d_%d" % (themeId, catIdx)
            catscanFile = os.path.join(app.CATSCANDIR, name, "%s.csv" % categoryName)
            category = Category(app, catId, catscanFile, categoryName, True)
            self.categories.append(category)

    def check_articles_in_osm(self):
        """Create two lists with titles of tagged/not tagged articles
        """
        self.titles = []
        self.titlesInOSM = []
        self.titlesNotInOSM = []
        for category in self.categories:
            self.titles.extend(category.allTitles)
            self.titlesInOSM.extend(category.allTitlesInOSM)
        self.titles = list(set(self.titles))
        self.titlesInOSM = list(set(self.titlesInOSM))
        self.titlesNotInOSM = [t for t in self.titles if not t in self.titlesInOSM]


class Regions:
    def __init__(self, app):
        names = ["Abruzzo", "Basilicata", "Calabria", "Campania",
                 "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio",
                 "Liguria", "Lombardia", "Marche", "Molise", "Piemonte",
                 "Puglia", "Sardegna", "Sicilia", "Toscana",
                 "Trentino-Alto Adige", "Umbria", "Valle d'Aosta",
                 "Veneto"]
        self.regionsList = []
        for regId, name in enumerate(names):
            region = Region(app, name.replace(" ", "_"), regId)
            self.regionsList.append(region)


class Region:
    def __init__(self, app, name, regId):
        self.name = name
        self.subcategories = []
        for theme in app.themes:
            for category in theme.categories:
                for subcategory in category.subcategories:
                    if subcategory.name.endswith(self.name):
                        self.subcategories.append(subcategory)
        self.subcategories.sort(key=operator.attrgetter("name"), reverse=False)
        self.articles = []
        self.articles_html = ""
        self.html = ""


class Category:
    """
    A category of Wikipedia

    articles, list of instances of Article class
    titles, list of titles (strings) of mappable articles
    titlesInOSM, list of titles (strings) of mappable articles already tagged in OSM
    osmIds, list of OSM objects
    html, html code of web page
    """
    def __init__(self, app, catId, catscanFile, categoryName, mappable, mainCategory=None, categoriesData=None):
        self.app = app
        self.ident = catId
        self.typ = "Categoria"
        self.name = categoryName
        if mainCategory is None:
            #A mainCategory is a category with a catsan file and a
            #dedicated webpage
            self.mainCategory = self
            self.mainCategory.allSubcategories = []
            self.updateTime = self.app.categoriesDates[self.name.encode("utf-8")]
        else:
            self.mainCategory = mainCategory
        self.wikipediaUrl = "http://it.wikipedia.org/wiki/Categoria:%s" % urllib.quote_plus(self.name.encode("utf-8"))

        #Extract categories info from catscan data
        #print "\n- reading catscan data"
        if categoriesData is None:
            categoriesData = self.read_categories_data(catscanFile, self.name)

        #Initialize attributes
        self.subcategories = []
        #Articles of the category
        self.articles = []
        #Articles of cateogry + articles of its subcategories
        self.allArticles = []
        #Titles of mappable aarticles
        self.titles = []
        self.allTitles = []
        self.titlesInOSM = []
        self.allTitlesInOSM = []
        #If not all subcategories and articles are mappable
        #the switch that shows non mappable items will not be visible in webpages
        self.articlesAreAllMappable = True
        self.isAllMappable = True
        #OSM objects belonging to the Wikipedia category
        self.osmIds = []
        self.allOsmIds = []

        #Mappable or not
        if not mappable or self.mainCategory.name in self.app.nonMappable and self.name in self.app.nonMappable[self.mainCategory.name]["subcategories"]:
            #print "not mappable category", self.name
            self.isMappable = False
        else:
            self.isMappable = True

        #Build articles
        for artIdx, articleName in enumerate(categoriesData[categoryName]["articles"]):
            artId = "%s_%d" % (self.ident, artIdx)
            article = Article(app, artId, articleName)
            article.set_mappable(self.mainCategory, self)
            self.articles.append(article)
            self.allArticles.append(article)
            if not article.isMappable:
                self.articlesAreAllMappable = False
                self.isAllMappable = False

        #Build subcategories
        for subIdx, subcatName in enumerate(categoriesData[categoryName]["subcategories"]):
            subIdx = "%s_%s" % (self.ident, subIdx)
            subcategory = Category(app, subIdx, catscanFile, subcatName, self.isMappable, self.mainCategory, categoriesData)
            self.subcategories.append(subcategory)
            self.allArticles.extend(subcategory.allArticles)

        #Check if completelyMappable. If the category is not completely
        #mappable, a link will appear on webpages to show not mappable categories
        if self.isAllMappable:
            for subcategory in self.subcategories:
                if not subcategory.isMappable or not subcategory.isAllMappable:
                    self.isAllMappable = False
                    break

        #Check if this category is a duplicate subcategory of mainCategory
        #mainCategory == one webpage
        """if self.name in [c.name for c in self.mainCategory.allSubcategories]:
            self.isDuplicate = True
        else:
            self.isDuplicate = False"""
        self.mainCategory.allSubcategories.append(self)

        self.articles_html = ""
        self.html = ""

    def read_categories_data(self, catscanFile, category):
        """Extract categories data from catscan
        """
        #print "\n- Leggi categorie-sottocategorie-articoli"
        #categoriesData =
        # {cat1: {subcat1: None, subcat2: None, "articles": ["article1", ...]},

        categoriesData = {}
        filename = "%s" % catscanFile
        file_in = open(filename, "r")
        lines = file_in.readlines()
        file_in.close()

        for i, line in enumerate(lines):
            values = line[:-2].split("\t")
            level, name, categories = values[0], values[1], values[2]
            name = name.decode("utf-8")
            if level in ("1", "2", "6", "10"):
                #  1 link to a Talk page
                #  2 Link to other kind of page, for example: a user page
                #  6 Link to a file, for example: an image
                # 10 Link to a template page
                continue
            for categoryName in categories.split("|"):
                categoryName = categoryName.decode("utf-8")
                if categoryName not in categoriesData:
                    categoriesData[categoryName] = {"articles": [],
                                                    "subcategories": []}
                if level == "0":
                    rowType = "articles"
                else:
                    rowType = "subcategories"
                categoriesData[categoryName][rowType].append(name)

        #Cleanup. Remove empty categories
        isClean = False
        while not isClean:
            categoriesData, isClean = self.remove_categories_without_data(categoriesData)
        return categoriesData

    def remove_categories_without_data(self, categoriesdata):
        isClean = True
        categoriesData_foo = deepcopy(categoriesdata)
        for catName in categoriesData_foo:
            data = categoriesData_foo[catName]
            if data["subcategories"] == [] and data["articles"] == []:
                #category without subcategories nor articles
                del categoriesdata[catName]
                self.app.categoriesWithoutData.append(catName)
                isClean = False
            for subcatName in data["subcategories"]:
                if subcatName not in categoriesData_foo:
                    #there aren't data reagarding this category from catscan
                    self.app.categoriesWithoutData.append(subcatName)
                    categoriesdata[catName]["subcategories"].remove(subcatName)
                    isClean = False
        return categoriesdata, isClean

    def print_category_tree_to_file(self):
        """Save the category tree to a text file (for debugging)
        """
        text = self.create_category_graph("", True)
        dict_file = open(os.path.join("data", "logs", "%s_dict.txt" % self.name), "w")
        dict_file.write(text)
        dict_file.close()

    def check_articles_in_osm(self):
        """Add to articles and categories informations regarding their
           status in OSM (if they are tagged or not)
        """
        for subcategory in self.subcategories:
            if subcategory.isMappable:
                subcategory.check_articles_in_osm()
        #articles in category
        for article in self.articles:
            if article.isMappable:
                if not hasattr(article, "inOSM"):
                    article.check_if_in_osm()
                self.titles.append(article.name)
                if article.inOSM:
                    self.titlesInOSM.append(article.name)
                    self.osmIds.extend(article.osmIds)
        #articles in subcategories
        self.allTitles.extend(self.titles)
        self.allTitlesInOSM.extend(self.titlesInOSM)
        self.allOsmIds.extend(self.osmIds)
        for subcategory in self.subcategories:
            if subcategory.isMappable:
                self.allTitles.extend(subcategory.allTitles)
                self.allTitlesInOSM.extend(subcategory.allTitlesInOSM)
                self.allOsmIds.extend(subcategory.allOsmIds)
        #remove duplicate
        self.allTitles = list(set(self.allTitles))
        self.allTitlesInOSM = list(set(self.allTitlesInOSM))
        self.allOsmIds = list(set(self.allOsmIds))

        #Calculate mapping progress
        # articles
        self.progress = {}
        if self.titles != []:
            #print "articles"
            self.progress["articles"] = {"num": None, "string": None}
            self.progress["articles"]["string"], self.progress["articles"]["num"] = self.calculate_tagging_progress(self.titlesInOSM, self.titles)
        # category
        if self.allTitles != []:
            self.progress["allMArticles"] = {"num": None, "string": None}
            self.progress["allMArticles"]["string"], self.progress["allMArticles"]["num"] = self.calculate_tagging_progress(self.allTitlesInOSM, self.allTitles)

    def calculate_tagging_progress(self, taggedArticles, allArticles):
        """Return tagging progress
        """
        progressString = "%s/%d" % (len(taggedArticles), len(allArticles))
        progressNum = float(len(taggedArticles)) / float(len(allArticles))
        return progressString, progressNum

    def set_has_template_in_articles(self):
        for article in self.articles:
            self.set_has_template_in_article(article)
        for subcategory in self.subcategories:
            if subcategory.isMappable:
                subcategory.set_has_template_in_articles()
        titlesWithoutTemplates = [article.name for article in self.allArticles if hasattr(article, "hasTemplate") and not article.hasTemplate]
        titlesWithoutTemplates = list(set(titlesWithoutTemplates))
        self.missingTemplatesNum = len(titlesWithoutTemplates)

    def set_has_template_in_article(self, article):
        if article.isMappable and article.inOSM and not hasattr(article, "hasTemplate"):
            if article.name not in self.app.templatesStatus:
                print "* Errore: articolo non presente nel dizionario templatesStatus:", article.name.encode("utf-8")
            else:
                if self.app.templatesStatus[article.name] == "True":
                    article.hasTemplate = True
                else:
                    article.hasTemplate = False

    def check_articles_coords_in_wikipedia(self):
        """Add coordinates to those articles that are not yet in OSM but
           whose coordinates are known by Wikipedia
        """
        for article in self.articles:
            self.check_article_coords_in_wikipedia(article)
        for subcategory in self.subcategories:
            if subcategory.isMappable:
                subcategory.check_articles_coords_in_wikipedia()
        titlesWithCoords = [article.name for article in self.allArticles if hasattr(article, "wikipediaCoords")]
        titlesWithCoords = list(set(titlesWithCoords))
        self.wikipediaCoordsNum = len(titlesWithCoords)

    def check_article_coords_in_wikipedia(self, article):
        scanFile = open(os.path.join("data", "nuts4nuts", "articles_to_scan.txt"), "a+")
        if article.isMappable and not article.inOSM:
            #Check if Wikipedia coordinates are known (from new_C.gz)
            if article.name in self.app.titlesCoords:
                article.wikipediaCoords = self.app.titlesCoords[article.name]
                article.wikipediaCoordsSource = 'Template:Coord'
                self.app.titlesWithCoordsFromWikipedia[article.name] = article.wikipediaCoords
            else:
                #create list of titles without coordinates, needed by Nuts4Nuts
                scanFile.write(article.name.encode('utf-8') + '\n')
        scanFile.close()

    def check_articles_coords_from_nuts4nuts(self):
        """Add coordinates to those articles that are not yet in OSM but
           whose coordinates are infered from Wikipedia with Nuts4Nuts
        """
        for article in self.articles:
            self.check_article_coords_from_nuts4nuts(article)
        for subcategory in self.subcategories:
            if subcategory.isMappable:
                subcategory.check_articles_coords_from_nuts4nuts()
        titlesWithCoords = [article.name for article in self.allArticles if hasattr(article, "wikipediaCoords")]
        titlesWithCoords = list(set(titlesWithCoords))
        if hasattr(self, "wikipediaCoordsNum"):
            self.wikipediaCoordsNum += len(titlesWithCoords)
        else:
            self.wikipediaCoordsNum = len(titlesWithCoords)

    def check_article_coords_from_nuts4nuts(self, article):
        if article.isMappable and not article.inOSM and \
           article.name in self.app.titlesNutsCoords:
            article.wikipediaCoords = self.app.titlesNutsCoords[article.name]
            article.wikipediaCoordsSource = 'Nuts4Nuts'
            self.app.coordsFromNuts4Nuts.append(article.name)

### print category info ################################################
    def print_info(self):
        """Print info about this category (for debugging)
        """
        print "\nName: %s" % self.name.replace("_", " ").encode("utf-8")
        print "Mappable subcategories (%d):" % len(self.subcategories)
        for subcat in self.subcategories:
            print "             %s" % subcat.name.replace("_", " ").encode("utf-8")
        print "Tagged articles: %s (%d)" % (self.progress["allMArticles"]["string"],
                                            self.progress["allMArticles"]["num"])
        print "Graph:"
        categoryGraph = self.create_category_graph("", True)
        print categoryGraph

    def create_category_graph(self, tree, last):
        """Print a graphic of category data (for debugging)
        """
        rows = ""
        #category name
        nonMappable = "(NON MAPPABLE) "
        categoryName = self.name.replace("_", " ").encode("utf-8")
        if not self.isMappable:
            categoryName = nonMappable + categoryName
        categoryName = " " + categoryName
        if tree == "":
            row = "  " + categoryName
        else:
            row = tree + "|_" + categoryName
        rows += "\n" + row

        if last:
            tree += "  "
        else:
            tree += "| "
        #articles names
        for article in self.articles:
            articleName = article.name.replace("_", " ").encode("utf-8")
            if not article.isMappable:
                articleName = nonMappable + articleName
            else:
                if article.inOSM:
                    articleName = "(TAGGED) " + articleName
            articleName = " " + articleName
            row = tree
            if self.subcategories != []:
                row += "|" + " " * (len(categoryName) - 2)
            else:
                row += " " * (len(categoryName) - 1)
            row += "|_" + articleName
            rows += "\n" + row

        #subcategories
        for i, subcategory in enumerate(self.subcategories):
            if i == len(self.subcategories) - 1:
                last = True
            else:
                last = False
            rows += subcategory.create_category_graph(tree, last)
        return rows

    #Create JSON file with category data, for debugging
    #or visualization (d3.js)
    def build_json_tree(self):
        """Build a nested dictionary of category for d3.js, with
           categories and articles as nodes
        """
        tree = {}
        tree["name"] = self.name.replace("_", " ")
        tree["size"] = self.allArticles
        children = []
        if self.articles != []:
            for article in self.articles:
                children.append({"name": article.name.replace("_", " ")})
        for subcategory in self.subcategories:
            subcategoryDict = subcategory.build_json_tree()
            children.append(subcategoryDict)
        tree["children"] = children
        return tree

    def build_json_tree_1(self):
        """Build a nested dictionary of category for d3.js, with
           Categories as node, articles as node attributes
        """
        tree = {}
        tree["name"] = self.name.replace("_", " ")
        tree["size"] = self.allArticles
        tree["articles"] = []
        if self.articles != []:
            tree["articles"] = [article.name.replace("_", " ") for article in self.articles]
        children = []
        for subcategory in self.subcategories:
            subcategoryDict = subcategory.build_json_tree_1()
            children.append(subcategoryDict)
        if children != []:
            tree["children"] = children
        return tree

    def write_json_file(self):
        import json
        ifile = open("./outjson.json", "w")
        data = json.dumps(self.build_json_tree(), indent=4)
        ifile.write(data)
        ifile.close()


class Article:
    def __init__(self, app, artId, name):
        """A Wikipedia article
        """
        self.app = app
        self.ident = artId
        self.typ = "Articolo"
        self.name = name
        self.wikipediaUrl = "http://it.wikipedia.org/wiki/%s" % urllib.quote_plus(self.name.encode("utf-8"))
        self.wiwosmUrl = "http://toolserver.org/~kolossos/openlayers/kml-on-ol-json3.php?lang=it&title=%s" % self.name.encode("utf-8")

    def check_if_in_osm(self):
        if self.name in self.app.taggedTitles:
            self.inOSM = True
            self.osmIds = self.app.taggedTitles[self.name]
        else:
            self.inOSM = False
            self.osmIds = []

    def set_mappable(self, mainCategory, parentCategory):
        if not parentCategory.isMappable or \
                mainCategory.name in self.app.nonMappable and \
                (self.name in self.app.nonMappable[mainCategory.name]["articles"] or
                 self.name in self.app.nonMappable[mainCategory.name]["redirects"]):
            #print "not mappable article", self.name
            self.isMappable = False
        else:
            self.isMappable = True
