# Original scraper: stations found by looking at maps
# Can include changes etc
# Up to approximately 2h15
from lxml import etree
from lxml.etree import tostring
from datetime import datetime
import scraperwiki
import StringIO

# Parameters for the scraper: stations, radius etc.
stations = [ {'Cambridge':6473}]

MIN_PRICE = 200000
MAX_PRICE = 310000
MIN_BEDROOMS = 2
RADIUS_MILES = 3.0
stop_phrases = [ "views over the garden",
"views over the rear garden", "views over the front garden",
"views over rear garden", "views over front garden",
"views across the gardens", "views onto the garden",
"in need of updating", "in need of modernisation",
"views over rear aspect", "views over front aspect",
"views over the rear aspect", "views over the front aspect",
"views over side aspect", "views over the side aspect",
"1970s",  "bungalow", "bunaglow",
"views to the front garden", "views to the rear garden" ]
# "semi detached", "semi-detached", "semidetached",
DOMAIN = 'http://www.rightmove.co.uk' 

def scrape_individual_house(house_url, town):
    HOUSE_URL = (DOMAIN + house_url).split('/svr/')[0]
    #print 'Scraping %s' % HOUSE_URL
    house_html = scraperwiki.scrape(HOUSE_URL)
    house_parser = etree.HTMLParser()
    house_tree = etree.parse(StringIO.StringIO(house_html), house_parser)
    house_text = house_tree.xpath('string(//div[@class="propertyDetailDescription"])')
    # Only look at houses with the word 'views' in the ad text. 
    if 'views' in house_text.lower() or 'elevated position' in house_text.lower():
        house = {}
        stopped_phrase = None
        # Check for stop phrases
        title = house_tree.xpath('string(//h1[@id="propertytype"])')
        for sp in stop_phrases:
            if (sp in house_text.lower()):
                #print 'Ignoring %s because of stop phrase: %s' % (HOUSE_URL, sp)
                stopped_phrase = sp
            if (sp in title.lower()):
                stopped_phrase = sp
        #if not any(d.get('link') == HOUSE_URL for d in house_items):
        image_url = tostring(house_tree.xpath('//img[@id="mainphoto"]')[0])
        price = house_tree.xpath('string(//div[@id="amount"])')
        nearby_stations = house_tree.xpath('string(//div[@id="nearbystations"]/div)')
        ns = nearby_stations.split("(")
        distance = ns[-1].replace(")","")
        distance = ' '.join(distance.split()).strip()
        if float(distance.replace(" miles",""))>1.5:
            return False
        map_img = house_tree.xpath('//a[@id="minimapwrapper"]/img')
        if map_img:
            map_img = tostring(house_tree.xpath('//a[@id="minimapwrapper"]/img')[0])
        else:
            map_img = ''
        house['title'] = "%s - %s, %s, %s from station" % (title, town, price, distance)
        #print 'HOUSE FOUND! %s, %s ' % (house['title'], HOUSE_URL)
        item_text = '<a href="' + HOUSE_URL + '">' + image_url + '</a>'
        #item_text += '<div style="position:relative;">'
        item_text += '<a href="' + HOUSE_URL + '">' + map_img + '</a>'
        #item_text += '<img id="googlemapicon" src="http://www.rightmove.co.uk/ps/images11074/maps/icons/rmpin.png"'
        #item_text += ' style="position:absolute;top:100px;left:100px;alt="Property location" /></div>'
        item_text += house_text
        item_text = item_text.replace("views","<span style='font-weight:bold;color:red;'>views</span>")
        house['description'] = item_text.replace("fireplace","<span style='font-weight:bold;color:red;'>fireplace</span>")
        if stopped_phrase:
            house['stop'] = stopped_phrase
        else:
            house['stop'] = ''
        house['link'] = HOUSE_URL
        house['pubDate'] = datetime.now()
        scraperwiki.sqlite.save(['link'], house)

# Gather list of results for an individual station. 
def scrape_results_page(results_url, town, initial=False):
    results_url = DOMAIN + results_url
    html = scraperwiki.scrape(results_url)
    parser = etree.HTMLParser()
    tree = etree.parse(StringIO.StringIO(html), parser)
    house_links = tree.xpath('//ol[@id="summaries"]//a[starts-with(text(), "More details")]/@href')
    for house_link in house_links:
        scrape_individual_house(house_link, town)
    if initial:
        results_links = tree.xpath('//ul[@class="items"]//a/@href')
        for r in results_links:
            scrape_results_page(r, town)

scrape_individual_house('/property-for-sale/property-33036143.html/svr/3113','Castle Cary')

# Go through each station: scrape each set of results in turn. 
for station in stations:
    station_name = station.keys()[0].title()
    print 'Scraping %s' % station_name
    station_id = station.values()[0]
    url1 = '/property-for-sale/find.html?locationIdentifier=STATION^%s&minPrice=%s&maxPrice=%s' % (station_id, MIN_PRICE, MAX_PRICE)
    url2 = '&minBedrooms=%s&displayPropertyType=houses&oldDisplayPropertyType=houses&radius=%s' % (MIN_BEDROOMS, RADIUS_MILES)
    # displayPropertyType=detachedshouses
    INITIAL_URL = url1 + url2
    scrape_results_page(INITIAL_URL, town=station_name, initial=True)
