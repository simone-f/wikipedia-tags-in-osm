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

"""Create webpages with the lists of Wikipedia categories and articles
"""

import os
import urllib
from data_manager import Category, Article
from subprocess import call
from jinja2 import Environment, FileSystemLoader


### Helpers ############################################################
class Helpers:
    def __init__(self, app):
        self.app = app

    def wikipedia_link(self, item):
        text = item.name.replace("_", " ").replace("\"", "&quot;")
        if isinstance(item, Article):
            itemType = self.app._("article")
        elif isinstance(item, Category):
            itemType = self.app._("category")
        title = self.app._("See {0}: {1}").format(itemType, text)
        cssClass = ' class="wikipedia_link"'
        link = self.url_to_link(item.wikipediaUrl, title, text, None, cssClass)
        return link

    def osm_ids_string_for_overpass(self, osmIds):
        """Return an OSM ids string used by Overpass
        """
        osmTypeAbbr = {"n": "node", "w": "way", "r": "relation"}
        osmIdsString = ""
        for osmId in osmIds:
            osmIdsString += '%s(%s);' % (osmTypeAbbr[osmId[0]], osmId[1:])
        return osmIdsString

    def overpass_query(self, item):
        if isinstance(item, Article):
            elementsString = self.osm_ids_string_for_overpass(item.osmIds)
        elif isinstance(item, Category):
            elementsString = self.osm_ids_string_for_overpass(item.allOsmIds)
        else:
            #wrongTags and badTags are not articles nor categories
            elementsString = self.osm_ids_string_for_overpass(item)
        query = '('
        query += elementsString
        query += ');'
        query += '(._;>;);'
        query += 'out meta qt;'
        return query

    def josm_link(self, mode, data, img):
        url = "http://localhost:8111/"
        if mode == "download":
            url += "import?url=http://overpass.osm.rambler.ru/cgi/interpreter?data=" + data
            title = self.app._("Download in JOSM")
        elif mode == "load_and_zoom":
            left = data[1] - 0.0005
            right = data[1] + 0.0005
            top = data[0] + 0.0005
            bottom = data[0] - 0.0005
            url += "load_and_zoom?left=%f&amp;right=%f&amp;top=%f&amp;bottom=%f" % tuple((left, right, top, bottom))
            title = self.app._("Zoom with JOSM nearby the object that must be tagged")
        link = self.url_to_link(url, title, None, img)
        return link

    def edit_link(self, data, img, zoom=17, editor='iD'):
        url = "http://www.openstreetmap.org/edit?"
        if editor == 'iD':
            url += 'editor=id'
        elif editor == 'Potlatch2':
            url += 'editor=potlatch2'
        url += '#map=%s/%s/%s' % (zoom, data[0], data[1])
        title = self.app._("Zoom with browser, {0} editor, nearby the object that must be tagged").format(editor)
        link = self.url_to_link(url, title, title, img)
        return link

    def overpass_turbo_link(self, query, cssClass=""):
        url = 'http://overpass-turbo.eu/index.html?Q=%s&amp;R' % urllib.quote_plus(query)
        title = self.app._("View as clickable map, image... (Overpass Turbo)")
        img = "{{root}}img/Overpass-turbo.png"
        if cssClass != "":
            cssClass = ' class="%s"' % cssClass
        link = self.url_to_link(url, title, None, img, cssClass)
        return link

    def osm_ids_string(self, item):
        osmTypeAbbr = {"n": "node", "w": "way", "r": "relation"}
        links = {"nodes": [], "ways": [], "relations": []}
        if isinstance(item, Article):
            osmIds = item.osmIds
        else:
            #item == ids of wrongTags or badTags
            osmIds = item
        #create links to OSM web pages
        for osmId in osmIds:
            url = "http://www.openstreetmap.org/browse/%s/%s" % (osmTypeAbbr[osmId[0]], osmId[1:])
            link = self.url_to_link(url, "%s" % self.app._("Go to OSM web page of this object"), osmId[1:])
            links[osmTypeAbbr[osmId[0]] + "s"].append(link)
        osmIdsString = ""
        for osmType, linksList in links.iteritems():
            if len(linksList) > 0:
                if osmIdsString != "":
                    osmIdsString += "<br />"
                img = '<img title="%s" src="%s%s.png">' % (osmType[:-1], "{{root}}img/", osmType)
                osmIdsString += "%s %s" % (img, ", ".join(linksList))
        if isinstance(item, Article):
            #put the string into a div
            osmDivId = item.ident
            osmIdsString = '<div id="%s" style="display:none"><br />%s</div>' % (osmDivId, osmIdsString)
        return links, osmIdsString

    def missing_template_link(self, article):
        img_title = self.app._("Wikipedia page is missing the coordinates' template")
        img_src = "{{root}}img/no_template.png"
        img_tag = '<img src="{src}" title="{title}"'\
                  ' class="articleLinkImg" />'.format(src=img_src,
                                                      title=img_title)
        span_tag = '<span class="missing_template_alert" {{data}}>'\
                   '{img}</span>'.format(img=img_tag)

        if article.OSMcoords:
            lat = article.OSMcoords[0]
            lon = article.OSMcoords[1]
            dim = article.OSMdim
            wikipedia_title = urllib.quote_plus(article.name.encode("utf-8"))

            a_tag = '<a href="../app/login?lat={lat}&lon={lon}">'\
                    '{{span}}</a>'.format(lat=lat, lon=lon)

            data = 'data-lat="{lat}" data-lon="{lon}" '\
                   'data-dim="{dim}" '\
                   'data-wikipedia="{title}"'.format(lat=lat,
                                                     lon=lon,
                                                     dim=dim,
                                                     title=wikipedia_title)

            span_tag = span_tag.format(data=data)
            link = a_tag.format(span=span_tag)

        else:
            span_tag = span_tag.format(data='')
            link = span_tag

        return link

    def add_tags_link(self, category):
        url = "http://toolserver.org/~kolossos/osm-add-tags/index.php?"
        url += "lang=it"
        url += "&amp;bbox=%s" % self.app.COUNTRYBBOX
        url += "&amp;cat=%s" % urllib.quote_plus(category.name.encode("utf-8"))
        url += "&amp;key=*&amp;value=*&amp;basedeep=10&amp;types=*&amp;request=Submit&amp;iwl=yes"
        title = self.app._("Search the objects in OSM by name and tag them automatically (WIWOSM add-tags)")
        img = "{{root}}img/add-tags.png"
        link = self.url_to_link(url, title, None, img)
        return link

    def url_to_link(self, url, title, text, img=None, cssClass="", target=""):
        """Return a link from some parameters
        """
        if target is None:
            target = ""
        else:
            target = ' target="_blank"'
        if img is not None:
            textOrImg = '<img src="%s" class="articleLinkImg">' % img
        else:
            textOrImg = text
        code = '<a href="%s" title="%s"%s%s>%s</a>' % (url, title, target, cssClass, textOrImg)
        return code

    def tagged_article_links(self, article):
        """Create links for tagged article from OSM objects to various
           services
        """
        #WIWOSM link
        wiwosmUrl = "http://toolserver.org/~kolossos/openlayers/kml-on-ol-json3.php?lang=%s&amp;title=%s" % (self.app.WIKIPEDIALANG, article.name)
        wiwosmTitle = self.app._("See Wikipedia map (WIWOSM)")
        wiwosmImg = "{{root}}img/wiwosm.png"
        wiwosmLink = self.url_to_link(wiwosmUrl, wiwosmTitle, None, wiwosmImg)

        #Show a div with OSM ids of the article
        #osm ids div
        osmLinks, osmIdsDiv = self.osm_ids_string(article)
        #link for showing the div
        osmUrl = "javascript:showHideDiv(\'%s\');" % article.ident
        osmLinkTitle = self.app._("See OSM web page")
        #check what kinds of OSM primitive are tagged and use the
        #right icon
        osmTypeAbbr = [osmType[0] for osmType in osmLinks if osmLinks[osmType] != []]
        osmLinkImg = "{{root}}img/osm_%s.png" % "".join(sorted(osmTypeAbbr))
        osmLink = self.url_to_link(osmUrl, osmLinkTitle, None, osmLinkImg, "", None)

        query = self.overpass_query(article)

        #JOSM remote control link
        img = "{{root}}img/josm.png"
        josmLink = self.josm_link("download", query, img)

        #Overpass Turbo link
        overpassTurboLink = self.overpass_turbo_link(query)

        code = '\n      %s ' % wiwosmLink
        code += '\n      %s ' % osmLink
        code += '\n      %s ' % josmLink
        code += '\n      %s' % overpassTurboLink
        if self.app.args.show_missing_templates and hasattr(article, "hasTemplate"):
            if not article.hasTemplate:
                code += '\n      %s' % self.missing_template_link(article)
        code += '\n      %s' % osmIdsDiv
        return code

    def non_tagged_article_links(self, article):
        """Create links to various services for an article not tagged in OSM yet
        """
        if hasattr(article, "wikipediaCoords"):
            #the article is not tagged but Wikipedia knows its coordinates
            img = "{{root}}img/josm_load_and_zoom.png"
            img_id = "{{root}}img/id.png"
            if article.wikipediaCoordsSource == 'Nuts4Nuts':
                img = "{{root}}img/josm_load_and_zoom_blue.png"
                img_id = "{{root}}img/id_blue.png"
            code = self.josm_link("load_and_zoom", article.wikipediaCoords,
                                  img)
            code += '\n      %s ' % self.edit_link(article.wikipediaCoords,
                                                   img_id)
        else:
            code = ""
        return code

    def header_needed(self, subitems, attributeName):
        """Return True or False if any subcategory has wikipediaCoordinates
           or misses Coord template. It is used to know if it is
           necessary to show headers in index tables
        """
        for subitem in subitems:
            if subitem.isMappable:
                if getattr(subitem, attributeName) > 0:
                    return True
        return False


### Webpages creator ###################################################
class Creator():
    def __init__(self, app, locale_langcode):
        self.app = app
        self.locale_langcode = locale_langcode
        self.env = Environment(extensions=['jinja2.ext.i18n',
                                      'jinja2.ext.autoescape'],
                          loader=FileSystemLoader("templates"),
                          trim_blocks=True,
                          lstrip_blocks=True)
        self.env.install_gettext_translations(self.app.translations)

        #When selectNonMappable==True the cells of tables in webpages
        #can be clicked, to create list of non mappable articles
        #or categories that can be copied into the file ./data/wikipedia/non_mappable
        selectNonMappable = True if app.clickable_cells == "true" else False
        app.tagsPerUser = sorted(self.app.users.items(), key=lambda x: x[1], reverse=True)

        #Create homepages
        self.stats_table = self.stats_table()
        self.homepages = {}

        #themes (index)
        self.render_index_template("index.html", "themes")

        #regions (index_1)
        if self.app.regions != []:
            self.render_index_template("index_1.html", "regions")

        #map (index_2)
        if self.app.args.show_link_to_wikipedia_coordinates:
            self.render_index_template("index_2.html", "map")

        #help (index_3)
        self.render_index_template("index_3.html", "help")

        #categories (subpages)
        helpers = Helpers(app)
        print " - render categories subpages"
        for theme in app.themes:
            for category in theme.categories:
                #articles
                category.articlesTable = ArticlesTable(app, category, selectNonMappable)
                #category
                for subcategory in category.subcategories:
                    subcategory.categoryTable = CategoryTable(app, subcategory, selectNonMappable)

                categoryTemplate = self.env.get_template('subpage.html')
                filename = "%s.html" % category.name

                category.html = categoryTemplate.render(app=self.app,
                                                        selectNonMappable=selectNonMappable,
                                                        helpers=helpers,
                                                        mode="themes",
                                                        root = '../../',
                                                        path = '/subpages/',
                                                        filename = filename,
                                                        item=category)
                category.html = category.html.replace('{{root}}', '../../')
                category.html = category.html.replace('{root}', '../../')

        #regions (subpages)
        if self.app.regions != []:
            print " - render regions subpages"
            for region in app.regions:
                for subcategory in region.subcategories:
                    subcategory.categoryTable = CategoryTable(app,
                        subcategory,
                        selectNonMappable)
                regionTemplate = self.env.get_template('subpage.html')
                filename = "%s.html" % region.name

                region.html = regionTemplate.render(app=self.app,
                                                    selectNonMappable=selectNonMappable,
                                                    helpers=helpers,
                                                    mode="regions",
                                                    root = '../../',
                                                    path = '/subpages/',
                                                    filename = filename,
                                                    item=region)

                region.html = region.html.replace('{{root}}', '../../')
                region.html = region.html.replace('{root}', '../../')

        #Create errors page
        print " - render errors page"
        errorsTemplate = self.env.get_template('errors.html')

        self.errorsHtml = errorsTemplate.render(app=self.app,
                                                root = '../',
                                                path = '/',
                                                filename = 'errors.html',
                                                helpers=helpers)
        self.errorsHtml = self.errorsHtml.replace('{{root}}', '../')

        #Create non_mappable page
        print " - render non_mappable page"
        nonMappableTemplate = self.env.get_template('non_mappable.html')

        self.nonMappableHtml = nonMappableTemplate.render(app=self.app,
                                                          root = '../',
                                                          path = '/',
                                                          filename = 'non_mappable.html',
                                                          helpers=helpers)

        #Save all HTML files
        self.save_html_files()

    def render_index_template(self, htmlFile, description):
        """Add to self.homepages the homepage file and
           its code rendered from a jinja2 template.
        """
        print " - render %s (%s)" % (htmlFile, description)
        indexTemplate = self.env.get_template(htmlFile)
        code = indexTemplate.render(app=self.app,
                                    root = '../',
                                    path = '/',
                                    filename = htmlFile,
                                    statsRows=self.stats_table)
        self.homepages[htmlFile] = code

    def stats_table(self):
        """Return html code of a table with the numbers of tagged/non tagged
           articles of the first and the last 9 days
        """
        red = "#cc0000"
        green = "#00cc7a"
        modes = [("to do", self.app._("Still to tag")),
                 ("mapped", self.app._("Tagged")),
                 ("total", self.app._("Total"))]

        #days for stats
        if len(self.app.dates) >= 11:
            dates = [self.app.dates[0]] + self.app.dates[-9:]
            days = [self.app.days[0]] + self.app.days[-9:]
        else:
            dates = self.app.dates
            days = self.app.days

        rows = [[self.app._("Articles")] + dates]
        for mode, description in modes:
            row = []
            row.append(description)
            #data
            for index, day in enumerate(days):
                value = int(day[mode])
                differenceStr = ""
                if index > 0:
                    previousValue = int(days[index - 1][mode])
                    difference = int(value) - previousValue
                    if difference != 0:
                        differenceStr = str(difference)
                        if difference > 0:
                            if mode == "to do":
                                color = red
                            else:
                                color = green
                            differenceStr = "+%s" % differenceStr
                        elif difference < 0:
                            if mode == "to do":
                                color = green
                            else:
                                color = red
                        differenceStr = ' <span style="color: %s">(%s)</span>' % (color, differenceStr)
                row.append("%s%s" % (str(value), differenceStr))
            rows.append(row)
        return rows

    def save_html_files(self):
        """Save webpages as html files
        """
        # homepage
        for fileName, homepage in self.homepages.iteritems():
            self.save_file(homepage, fileName)
        # categories pages
        for theme in self.app.themes:
            for category in theme.categories:
                categoryFile = "%s.html" % category.name
                self.save_file(category.html, categoryFile, subdir="subpages")
        # regions pages
        for region in self.app.regions:
            regionFile = "%s.html" % region.name
            self.save_file(region.html, regionFile, subdir="subpages")
        # errors page
        self.save_file(self.errorsHtml, "errors.html")
        # non_mapable page
        self.save_file(self.nonMappableHtml, "non_mappable.html")


    def save_file(self, text, fileName, subdir=None):

        # output directory (html/locale_locale_langcode)
        outDir = os.path.join(self.app.HTMLDIR, self.locale_langcode)
        if subdir:
            outDir = os.path.join(self.app.HTMLDIR,
                                  self.locale_langcode,
                                  subdir
                                  )

        # Try to make the directory, catch exception if it exists
        # (and skik creation)
        try:
            os.makedirs(outDir)
        except OSError as e:
            # skip directory creation
            # print 'Skipping directory {0} creation: {1}'.format(
            #     outDir, str(e.strerror))
            pass

        fileOut = open(os.path.join(outDir, fileName), "w")

        if isinstance(text, unicode):
            text = text.encode("utf-8")
        fileOut.write(text)
        fileOut.close()


### Subpage ############################################################
class ArticlesTable(Helpers):
    def __init__(self, app, item, selectNonMappable):
        """Return an html table with articles of a ctagory
        """
        self.attr = ''
        self.content = []
        self.app = app

        if item.articles != []:
            self.attr  += ' class="data"'
            rows = []
            if not item.articlesAreAllMappable:
                self.attr += ' id="%s_articles"' % item.ident

            for article in item.articles:
                rows.append([])

                #Article cell
                cssclass = ""
                colspan = ""
                if not article.isMappable:
                    cssclass = ' class="non_mappable"'
                    colspan = ' colspan="2"'
                onclick = ""
                if selectNonMappable:
                    onclick = ' onclick="getName(this);"'

                cell = {"attr": "%s%s%s" % (onclick, cssclass, colspan),
                        "content": self.wikipedia_link(article)}
                rows[-1].append(cell)

                #Article tagging status cell
                if article.isMappable:
                    if article.inOSM:
                        links = self.tagged_article_links(article)
                    else:
                        links = self.non_tagged_article_links(article)
                    cell = {"attr": "", "content": links}
                    rows[-1].append(cell)
            self.content = rows


class CategoryTable(Helpers):
    def __init__(self, app, category, selectNonMappable):
        """Return an html table with subcategories (and their articles)
           of a category
        """
        self.app = app
        self.selectNonMappable = selectNonMappable
        columnsNumber = self.table_columns_number(category) + 1

        self.attr = ' class="data"'
        if not category.isAllMappable:
            self.attr += ' id="%s"' % category.ident

        self.rows = [[]]
        self.build_table(category, columnsNumber)
        self.content = self.rows

    def table_columns_number(self, category, i=0):
        if category.subcategories != []:
            columnsNumber = max([self.table_columns_number(subcategory, i + 1) for subcategory in category.subcategories])
        else:
            columnsNumber = i
        return columnsNumber

    def build_table(self, category, columnsNumber, level=0):
        """Build table by recursively reading subcategories and articles
           of the category
        """
        articles = category.articles
        subcategories = category.subcategories
        isFirstItem = True

        #articles
        for article in articles:
            colspan = columnsNumber - level
            if not article.isMappable:
                colspan += 1
            if colspan > 1:
                colspan = " colspan=%s" % str(colspan)
            else:
                colspan = ""
            self.add_item(article, isFirstItem, colspan, "")
            isFirstItem = False
        #subcategories
        for subcategory in subcategories:
            rowsnumber = len(subcategory.allArticles)
            if rowsnumber > 1:
                rowspan = " rowspan=%s" % rowsnumber
            else:
                rowspan = ""
            self.add_item(subcategory, isFirstItem, "", rowspan)
            isFirstItem = False
            self.build_table(subcategory, columnsNumber, level + 1)

    def add_item(self, item, isFirstItem, colspan, rowspan):
        """Add a cell to the table
        """
        if not isFirstItem:
            #new row
            self.rows.append([])

        #attributes
        onclick = ""
        if self.selectNonMappable:
            onclick = ' onclick="getName(this);"'
        cssClasses = []
        if not item.isMappable:
            cssClasses.append("non_mappable")
        if isinstance(item, Category):
            cssClasses.append("category")
        if cssClasses == []:
            cssClass = ""
        else:
            cssClass = ' class="%s"' % " ".join(cssClasses)

        #category
        if isinstance(item, Category):
            catData = self.wikipedia_link(item)
            if not len(item.allTitles) == len(item.allTitlesInOSM):
                #add a link to WIWOSM tool "add-tags"
                catData += "\n %s" % self.add_tags_link(item)
            if item.allTitlesInOSM != [] and not self.selectNonMappable:
                #add a link to overpass for showing all objects
                query = self.overpass_query(item)
                linkClass = "overpassTurboLink"
                catData += "\n %s" % self.overpass_turbo_link(query, linkClass)

            cell = {"attr": "%s%s%s" % (onclick, rowspan, cssClass),
                    "content": catData}
            self.rows[-1].append(cell)

        #article
        if isinstance(item, Article):
            cell = {"attr": "%s%s%s" % (onclick, colspan, cssClass),
                    "content": self.wikipedia_link(item)}
            self.rows[-1].append(cell)

            if item.isMappable:
                #content
                if item.inOSM:
                    links = self.tagged_article_links(item)
                else:
                    links = self.non_tagged_article_links(item)
                #attributes
                nowrap = ""
                if links != "":
                    nowrap = " NOWRAP"

                #Article tagging status cell
                cell = {"attr": nowrap, "content": links}
                self.rows[-1].append(cell)


class Redirect():
    """Class to create the index.html to redirect to the preferred language"""
    def __init__(self, app, locale_langcode):
        print " - render redirect page to %s" % locale_langcode
        htmlFile = "redirect.html"
        self.app = app
        self.locale_langcode = locale_langcode
        self.env = Environment(extensions=['jinja2.ext.i18n',
                                           'jinja2.ext.autoescape'],
                               loader=FileSystemLoader("templates"),
                               trim_blocks=True,
                               lstrip_blocks=True)
        self.env.install_gettext_translations(self.app.translations)
        indexTemplate = self.env.get_template(htmlFile)
        code = indexTemplate.render(lang=locale_langcode)
        fileOut = open(os.path.join(self.app.HTMLDIR, 'index.html'), "w")

        if isinstance(code, unicode):
            code = code.encode("utf-8")
        fileOut.write(code)
        fileOut.close()
