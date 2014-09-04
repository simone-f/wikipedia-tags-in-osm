Wikipedia tags in OSM
---------------------
This program creates simple web pages with lists of Wikipedia articles, showing which ones are still to be tagged in OpenStreetMap (OSM).<br>
Its aim is to invite OSM mappers to add Wikipedia tags, by showing the progress of Wikipedia articles tagging in a specific country, regarding a selected list of *mappable* categories.

##Features:
* Download and parse OSM and Wikipedia data to show the tagging **progress** of selected Wikipedia categories, in the configured country
* Informations reagarding articles and their corresponding objects in OSM are provided through **links** to: [WIWOSM](https://wiki.openstreetmap.org/wiki/WIWOSM) map, OSM web pages, JOSM remote control and [Overpass Turbo](http://overpass-turbo.eu/). OSM objects belonging to the same category can be loaded on a map (downloaded, saved as image, etc...), through another Overpass Turbo link.
* Tools that help to **add tags**:
    * each category has a link to add-tags [service](http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags) (from Kolossos), where category name and country bounding box parameters are already filled in
    * a JOSM remote link lets the user zoom to the position of a non tagged article, if Wikipedia knows its position
* **Non-mappable** categories and articles can be added to a blacklist, so that they are not visible in web pages by default (e.g. "Paintings in X Museum").
* a warning icon marks articles **without template** (Coord).

Updated webpages for Italy can be found [here](http://geodati.fmach.it/gfoss_geodata/osm/wtosm/index.html) (thanks to [fmach.it](http://fmach.it) for hosting).

##Overview
Starting from a list of Wikipedia categories, written by the user in the 'config.cfg' file, the script:

0. downloads/updates the OSM data (PBF) of a country (from GEOFABRIK)
1. downloads subcategories and articles names of the selected Wikipedia categories (from Quick Intersection)
2. parses the OSM file, filtering the [tags](http://wiki.openstreetmap.org/wiki/Wikipedia) accepted by [WIWOSM](https://wiki.openstreetmap.org/wiki/WIWOSM) project
3. creates webpages to show which articles are already tagged and which ones are not, providing links to inspect how the objects have been mapped.

##Requirements
###Data
A POLY file with the same name of the country, e.g. `italy.poly`, must be put in `data/OSM` directory. It can be downloaded from [GEOFABRIK](http://download.geofabrik.de/).

###Programs
* python-lxml
* osmupdate
* osmconvert
* osmfilter
* wget
* python-jinja2
* python-babel
* zgrep, cut (if using --show_link_to_wikipedia_coordinates)
* python-requests (if using --infer_coordinates_from_wikipedia)

On 32 bit system, dwonload [osmconvert/update/filter](http://wiki.openstreetmap.org/wiki/Osmconvert) tools:

        sudo wget http://m.m.i24.cc/osmconvert32 -O /usr/bin/osmconvert
        sudo wget http://m.m.i24.cc/osmupdate32 -O /usr/bin/osmupdate
        sudo wget http://m.m.i24.cc/osmfilter32 -O /usr/bin/osmfilter
        sudo chmod +x /usr/bin/osmconvert /usr/bin/osmupdate /usr/bin/osmfilter
    
On 64 bit system, download and compile the programs as follow:
        wget -O - http://m.m.i24.cc/osmconvert.c | cc -x c - -lz -O3 -o osmconvert
        wget -O - http://m.m.i24.cc/osmfilter.c | cc -x c - -lz -O3 -o osmconvert
        wget -O - http://m.m.i24.cc/osmfilter.c | cc -x c - -lz -O3 -o osmconvert

##Usage

###Fill the config file
Create a copy of `config.template`, rename it as `config.cfg` and fill the following options:

* `osmdir`, the directory where you want to download national OSM data
* `osmbbox`, the bbox of the country (it will be used by WIWOSM add-tags tool)
* `preferred language`, Wikipedia lang, for example: 'it'
* `country`, the country name as used in GEOFABRIK repository, for example: 'italy'
* add one or more theme in `themes` section and add one or more Wikipedia categories to them. The script will then download subcategories and articles names from [Quick Intersection](http://tools.wmflabs.org/catscan2/quick_intersection.php). To refresh a category, just delete its file from `.data/wikipedia/catscan/themename`.

###Run the script
0. (Optional) Print categories in the project:

        launch_script.py --print_categories_list

1. Download OpenStreetMap data of the country:

        launch_script.py --download_osm
next time, just update the previously downloaded OSM data to the last minute (through osmupdate):

        launch_script.py --update_osm

2. Read Wikipedia data (categories -> subcategories -> articles), search tagged articles in the OSM file and create updated webpages:

        launch_script.py --create_webpages

####Other options
        
* Show JOSM link for zooming to the position of a non already tagged article, known by Wikipedia:

         launch_script.py --show_link_to_wikipedia_coordinates --create_webpages
       
* Show JOSM link for zooming to the position of a non already tagged article, whose coordinates have been infered with [Nuts4Nuts](https://github.com/SpazioDati/Nuts4Nuts)(see below for more info)

         launch_script.py --infer_coordinates_from_wikipedia --create_webpages

* Mark on the webpages the articles without Coord template on Wikipedia:

         launch_script.py --show_missing_templates --create_webpages

* Calculate OSM coordinates of articles (point for nodes, centroids for ways and relations) and suggest to use them when a Wikipedia article is missing Coord template:

         launch_script.py -t --show_coordinates_from_osm --create_webpages
                        
For the complete list of options run `launch_script.py -h`.

##Notes
###Translations
1. Create a translation catalog (PO file) for your language, e.g. DE:

        pybabel init -l de_DE -d ./locale -i ./locale/messages.pot
        
2. translate the strings in catalog, e.g. `locale/de_DE/LC_MESSAGES/de_DE.po`

3. compile catalog to binary MO file:

        pybabel compile -f -d ./locale

Submit your translation as a pull request.

###Non mappable categories or articles
Add the names of *non mappable* categories or articles (for example "Paintings in the X Museum") to the files `./data/wikipedia/non_mappable/subcategories` and `./data/wikipedia/non_mappable/articles`. The script will set them as invisible in the web pages.

If you need to add many names to 'non_mappable' file, set the option 'clickable_cells = true' in config file and create web pages again.<br>Now, by clicking on tables cells, a string of names will be automatically created on top of the page, ready to be copied and pasted to 'non_mappable' files.

Redirects aren't supported by WIWOSM, therefore they are not downloaded when Wikipedia categories data is requested to Quick Intersection. However, you can manually add a new redirect to `./data/wikipedia/non_mappable/redirects` so that it will be removed without having to download Wikipedia category data again.

###Infer coordinates with Nuts4Nuts
The first time the script is run with the option -n it infers the coordinates of Wikipedia articles without a geographic position. The coordinates are saved to the file 'data/nuts4nuts/nuts4nuts_LANG_coords.txt'. Since this can take a long time it is better to create the file on its own, by running 'python nuts4nuts_infer.py'. This script can be interrupted to scan more articles a little at a time.

###Workarounds
####Tagged articles not detected by the script
If the the script does not correctly detect a tag in the OSM file, add the article name and OSM objects ids to `./data/workaround/tagged.csv` (and fix the parser ;-)

####False positive errors
If the the script flag as error a tag which is considered correct (strange tags), add the tag to the file `./data/workaround/false_positive.csv` and the tag will not be flagged as error again.

###Debugging
For debugging purpose, categories trees can be print to text files, by setting `print categories to text files = true` option in the config file.

##Development
Authors: [Simone F.](http://wiki.openstreetmap.org/wiki/User:Groppo/) <groppo8@gmail.com> (main author), Luca Delucchi, Cristian Consonni

Contributors: dforsi, aborruso

Code: Python, license GPLv3

###Credits and attributions
This program has been inspired by JOSM's [Wikipedia Plugin](http://wiki.openstreetmap.org) and [add-tags](http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags) (Kolossos).

Services linked from the pages: [WIWOSM](http://wiki.openstreetmap.org/wiki/WIWOSM) (master, Kolossos), [add-tags](http://wiki.openstreetmap.org/wiki/JOSM/Plugins/RemoteControl/Add-tags) (Kolossos), [OverpassTurbo](http://overpass-turbo.eu/) (tyr.asd)

Services used by the program: MediaWiki [API](https://www.mediawiki.org/wiki/API:Main_page), [Wikipedia coordinates](https://toolserver.org/~kolossos/wp-world/pg-dumps/wp-world), [Nuts4Nuts](http://nuts4nutsrecon.spaziodati.eu/), [quick_intersection](http://tools.wmflabs.org/catscan2/quick_intersection.php) (Magnus Manske)

* themes icons are from [Maki](https://github.com/mapbox/maki), License BSD
* regions icons are from [araldicacivica.it](http://www.araldicacivica.it), License [CC BY-NC-ND 3.0](http://creativecommons.org/licenses/by-nc-nd/3.0/it/)
* nodes, ways, relations and Overpass Turbo icons are from the [OSM Wiki](http://wiki.openstreetmap.org/)