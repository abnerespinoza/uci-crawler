import re
import os
import json
import gzip
import hashlib

from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse


PAGES_DIRECTORY = 'pages'

visited = set()
ics_sub = dict()


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def save_page(url, html):
    Path(PAGES_DIRECTORY).mkdir(parents=True, exist_ok=True)
    
    # create hash from url (hash is irreversible)
    hash_object = hashlib.sha256(url.encode())
    hex_dig = hash_object.hexdigest()
    
    try:
        decoded_html = html.decode()
        
        content = {
            'url': url,
            'html': decoded_html
        }

        # create page with hash as name, then compresses the data
        with gzip.open(os.path.join(PAGES_DIRECTORY, str(hex_dig)), 'w') as fout:
            fout.write(json.dumps(content).encode('utf-8'))
            
        return True
    except:
        print('Cannot decode html for {}'.format(url))
        return False


def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    # checking status, page content
    if resp.status == 200:
        if not resp.raw_response or not resp.raw_response.content:
            return []
    else:
        return []
    
    found = []
    parsed = urlparse(url)
    
    # calculating metrics
    if parsed.netloc.endswith('.ics.uci.edu'):
        if parsed.netloc in ics_sub:
            ics_sub[parsed.netloc] += 1
        else:
            ics_sub[parsed.netloc] = 1

    # adding to set of visited, then saving states to files for redundancy
    visited.add(url)
    with open('records/visited.txt', 'w') as vi, open('records/ics_sub.txt', 'w') as ic:
        vi.write(str(visited))
        ic.write(str(ics_sub))
    
    # parsing, then saving webpage
    soup = BeautifulSoup(resp.raw_response.content, 'lxml')
    save_page(url, resp.raw_response.content)
    
    links = soup.find_all('a')
    for link in links:
        # skip to next iteration if no href attribute found
        if not link.has_attr('href'):
            continue
            
        parsedLink = urlparse(link['href'])
        
        newLink = 'https://'
        if parsedLink.scheme:
            newLink = parsedLink.scheme + '://'
            
        if parsedLink.netloc:
            newLink += parsedLink.netloc
        else:
            newLink += parsed.netloc
            
        # removing stray period
        path = parsedLink.path
        if path.startswith('.'):
            path = path[1:]
            
        # adding '/' if missing
        if not path.startswith('/'):
            path = '/' + path
        newLink += path
        
        # removed for consistency
        if newLink.endswith('/'):
            newLink = newLink[:-1] 
        
        # making all urls lowercase for consistency
        newLink = newLink.lower()
        
        found.append(newLink)
    
    return found


def isAllowed(parsed):       
    if ( 
         parsed.netloc.endswith('.ics.uci.edu')
         or parsed.netloc.endswith('.cs.uci.edu') 
         or parsed.netloc.endswith('.informatics.uci.edu') 
         or parsed.netloc.endswith('.stat.uci.edu')):
        return True
    
    if ( 
         parsed.netloc == 'ics.uci.edu'
         or parsed.netloc == 'cs.uci.edu'
         or parsed.netloc == 'informatics.uci.edu'
         or parsed.netloc == 'stat.uci.edu'):
        return True

    if parsed.netloc.endswith('.today.uci.edu') or parsed.netloc == 'today.uci.edu':
        if parsed.path.startswith('/department/information_computer_sciences'):
            return True

    return False


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    
    # replace date
    url = re.sub('\d{4}-\d{2}-\d{2}', 'xxxx-xx-xx', url)
        
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        if not isAllowed(parsed):
            return False
        
        if url in visited:
            return False
        
        if url.endswith('.bam'):
            return False
        
        if re.match(
             r".*\.(css|js|bmp|gif|jpe?g|ico"
             + r"|png|tiff?|mid|mp2|mp3|mp4"
             + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
             + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
             + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
             + r"|epub|dll|cnf|tgz|sha1"
             + r"|thmx|mso|arff|rtf|jar|csv"
             + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False
        
        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise