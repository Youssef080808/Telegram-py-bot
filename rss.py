'''import xml.etree.ElementTree as cElementTree
import requests

# Parses first 10 items from http://planetpython.org/rss20.xml and returns a list of 
# dictionaries with the title, link, and description of each item.
def parse_planetpy_rss():
    response = requests.get("http://planetpython.org/rss20.xml") # GET request to download the 
    # RSS feed from the specified URL
    parsed_xml = cElementTree.fromstring(response.content)# response.content contains the raw 
    #XML data from the RSS feed and fromstring() parses the XML data into an ElementTree object
    items = []
    for node in parsed_xml.iter():# iter() walks through all the nodes in the XML tree
        if node.tag == "item":# RSS feeds structure each blog post as an <item>
            item = {}
            for item_node in list(node): # look at tags inside <item> tag
                if item_node.tag == "title": 
                    item["title"] = item_node.text
                if item_node.tag == "link":
                    item["link"] = item_node.text
                    #EX:{'title': 'Some Blog Post Title', 'link': 'https://example.com/post'}
            items.append(item)
    return items[:10]# return the first 10 items from the list of dictionaries'''
import requests
response = requests.get("http://planetpython.org/rss20.xml")
print(response.status_code)
print(response.text[:500])

   