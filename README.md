Wikipedia tags in OSM
---------------------
This script creates simple web pages with lists of Wikipedia articles, showing which ones are still to be tagged in OpenStreetMap.

Starting from a list of Wikipedia categories written by the user in the 'config' file, the script:

0. downloads/updates a national OSM data file (from GEOFABRIK)
1. downloads Wikipedia data regarding the selected categories (from catscan), specifically: subcategories names and articles titles
2. parse the OSM file, looking for [tags](http://wiki.openstreetmap.org/wiki/Wikipedia) accepted by [WIWOSM](https://wiki.openstreetmap.org/wiki/WIWOSM) project
3. creates webpages for showing which articles are already tagged and which ones are not, providing links to inspect how the objects have been mapped (OSM website link, JOSM remote link, Overpass Turbo link).

Updated webpages for Italy can be found [here](http://geodati.fmach.it/gfoss_geodata/osm/wtosm/index.html) (thanks to [fmach.it](http://fmach.it) for hosting).

##About
Author: Simone F. <groppo8@gmail.com> [OSM Wiki](http://wiki.openstreetmap.org/wiki/User:Groppo/)

License: GPLv3

###Attributions
* themes icons: [Maki](https://github.com/mapbox/maki), License BSD
* regions icons: [araldicacivica.it](http://www.araldicacivica.it), License [CC BY-NC-ND 3.0](http://creativecommons.org/licenses/by-nc-nd/3.0/it/)
* nodes, ways, relations icons: [OSM Wiki](http://wiki.openstreetmap.org/)

---

##How to use
O.S.: Ubuntu 13.04

###Install dependencies
* python-lxml
* osmupdate
* osmconvert
* osmfilter
* wget

osm* tools can be downloaded and installed with:

        sudo wget http://m.m.i24.cc/osmconvert32 -O /usr/bin/osmconvert
        sudo wget http://m.m.i24.cc/osmupdate32 -O /usr/bin/osmupdate
        sudo wget http://m.m.i24.cc/osmfilter32 -O /usr/bin/osmfilter
        sudo chmod +x /usr/bin/osmconvert /usr/bin/osmupdate /usr/bin/osmfilter
    
On 64 bit system install 'ia32-libs' package to execute the previous 32 bit programs.

###How it works
The user writes in the './config' file the categories he/she is interested in.
The script: downloads informations about those categories (subcategories and articles) from Wikipedia (catscan), downloads or updates OSM data of the country from GEOFABRIK (through osmupdate), reads tags in file (python-lxml) and creates webpages.

###Fill the config file
Write in './config' file:

* 'osmdir', the directory where you want to download national OSM data
* 'preferred language', Wikipedia lang, for example: 'it'
* 'country', the country name as used in GEOFABRIK repository, for example: 'italy'
* (optional) add a Wikipedia category to the project, by adding its name to an existing theme, or to a new one, in 'themes' section. The script will then download its data (subcategories and articles names) from Wikipedia. To refresh a category, just delete its file in '.data/wikipedia/catscan/theme'.

###Run the script
0. (Optional) Print current categories in the project:

        launch_script.py --print_categories_list

1. Download OpenStreetMap data of the selected country:

        launch_script.py --download_osm
next time, just update the previously downloaded OSM data to the last minute, with osmupdate:

        launch_script.py --update_osm
    
2. Read Wikipedia data (categories -> subcategories -> articles), search tagged articles in the OSM file and create updated webpages:

        launch_script.py --create_webpages

###Non mappable categories or articles
If there are "non mappable" subcategories or articles inside a category, (for example "Paintings in the X Museum"), add their names to the file './data/wikipedia/non_mappable'. The script will set them as invisible in webpages.

If you need to add many names to 'non_mappable' file, set the option 'clickable_cells = true' in config file and create webpages again.<br>Now, by clicking on tables cells, a string of names will be automatically created on top of the page, ready to be copied and pasted to './data/wikipedia/non_mappable' file.

###Workaround
####Tagged articles not detected by the script
If the the script does not correctly detect a tag in the OSM file, add the article name and OSM objects ids to './data/workaround/tagged.csv' (and fix the parser ;-)

####False positive errors
If the the script flag as error a tag which is considered correct (strange tags), add the tag to the file './data/workaround/false_positive.csv' and the tag will not be flagged as error again.

###Other options
For debugging purpose, it is possible to print categories trees to text files, by setting 'print categories to text files = true' option in config file.

###Notes
To refresh catscan data of a category (its subcategories and articles) just delete its file in './data/wikipedia/catscan'.