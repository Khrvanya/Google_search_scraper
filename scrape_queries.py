from selenium import webdriver
# !pip install webdriver-manager   # might need it
from webdriver_manager.chrome import ChromeDriverManager
import psutil  # for terminating chromedriver

from bs4 import BeautifulSoup
import lxml  # for BeautifulSoup
from boilerpy3 import extractors

# https://stackoverflow.com/questions/37512311/cant-install-python-polyglot-package-on-windows
from polyglot.detect import Detector
import re
import nltk

lemma = nltk.wordnet.WordNetLemmatizer()

import pandas as pd
import json
import time

LOCAL_TIME = pd.to_datetime(time.ctime(time.time()))

import shutil
import stat  # some permission
import os
from sys import argv, getsizeof

from contextlib import contextmanager
import threading
from _thread import interrupt_main

SCRAPED_LANGUAGE = 'en'  # could be None == all
MIN_SCRAPED_SIZE = .35  # Kb
CURR_PATH = os.path.abspath(os.curdir)
QUERIES_PATH = os.path.join(CURR_PATH, 'queries')
# https://antcpt.com/eng/information/recaptcha-2-selenium.html
ANTICAPTCHA_PLUGIN_PATH = os.path.join(CURR_PATH,
                                       'anticaptcha-chrome-plugin_v0.50.crx')
ANTICAPTCHA_API_KEY = "22418f57f7cecf03fa24a38fb384f6fa"


def stop_app(app_exe):
    """
    Stops all app's processes
    """

    for process in psutil.process_iter():
        #         print(process)
        if process.name() == app_exe:
            process.terminate()


def create_new_folder(path):
    """
    Makes a new folder, even if there exists one
    """

    if os.path.exists(path):
        os.chmod(path, stat.S_IWRITE)  # permission
        shutil.rmtree(path)
    time.sleep(1)
    os.mkdir(path)


def make_filename_safe(filename: str) -> str:
    filename = "".join([c for c in filename if re.match(r'[\w,. ]', c)])
    return filename


def get_set_subset(origin_set, length):
    """
    Gets a origin_set subset of length
    """

    if len(origin_set) <= length:
        return origin_set
    else:
        assert length > 0, 'length should be positive'

    result_set = set()
    for i in origin_set:
        if len(result_set) == length:
            return result_set
        result_set.add(i)

    assert length == len(result_set), '!!!result_set length is wrong!!!'
    return result_set


def to_list(obj) -> list:
    if type(obj) == list:
        return obj
    return [obj]


# Method of sending API request for anti-captcha.com API KEY initialization into plaguin
# Works only on existing HTML page (https://antcpt.com/blank.html)
# Request won't work on about:blank page
def acp_api_send_request(driver, message_type, data=None):
    if data is None:
        data = {}
    message = {
        # always put such API receiver
        'receiver': 'antiCaptchaPlugin',
        # request type (setOptions)
        'type': message_type,
        # additional data
        **data
    }
    # run JS code on the page by sending message with window.postMessage
    return driver.execute_script("""
    return window.postMessage({});
    """.format(json.dumps(message)))


def run_chromedriver(**args):
    """
    Runs Selenium chromedriver without any settings
    ChromeDriverManager().install(): installs of finds path on its own
    """

    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), **args)
    except PermissionError:
        stop_app("chromedriver.exe")
        stop_app("chrome.exe")  #####
        time.sleep(2)
        driver = webdriver.Chrome(ChromeDriverManager().install(), **args)

    return driver


def run_anticaptcha_chromedriver(ANTICAPTCHA_API_KEY, ANTICAPTCHA_PLUGIN_PATH):
    """
    Runs Selenium chromedriver with anticaptcha extention
    To get ANTI_CAPTCHA_API_KEY register on anti-captcha.com
    To get ANTICAPTCHA_PLUGIN_PATH check all instructions on:
    https://antcpt.com/eng/information/recaptcha-2-selenium.html
    """

    options = webdriver.ChromeOptions()
    options.add_extension(ANTICAPTCHA_PLUGIN_PATH)

    driver = run_chromedriver(options=options)

    # Go to blank page for API request to plaguin
    driver.get('https://antcpt.com/blank.html')

    acp_api_send_request(
        driver,
        'setOptions',
        {'options': {'antiCaptchaApiKey': ANTICAPTCHA_API_KEY}}
    )

    # Pause for plaguin to verify anti-captcha.com API key
    time.sleep(3)

    return driver


def process_text(text: str) -> str:
    """
    Processes string: deletes stop words if there are some,
    makes string lower, deletes some sumbols, lemmatizes string
    """

    try:
        f = open('stopwords_english.txt', 'r')
        stopwords = f.read()
        f.close()
        stop_words_exist = True
    except:
        print("!!!stopwords hadnt been read!!!")
        stop_words_exist = False

    text = text.lower()
    text = re.findall(r"[a-z0-9]+_?'?&?-?[a-z0-9]+_?'?&?-?[a-z0-9]+", text)

    if stop_words_exist:
        text = [w for w in text if w not in stopwords]

    text = [lemma.lemmatize(w) for w in text]  # stemmer.stem_word(w)
    text = ' '.join(text)

    return text


def process_date(time: str):
    """
    Gets string time returns pandas Timestamp
    Works only with eng date!
    """

    try:
        date = pd.to_datetime(time)
    except:
        date = LOCAL_TIME

    return date


def get_link_per_gpage(links_number: int) -> tuple:
    """
    Gets the number of links to scrape, which is multiple by 10 !!
    Returns number of links per page and pages to scrape
    Example: gets 320, returns 10, 32
    """

    assert links_number % 10 == 0 and links_number >= 0, (
        '!!!links number must be multiple by 10 and be grater zero!!!')

    if links_number == 0:
        return 100, 5

    return 10, int(links_number / 10)


def timeout(timeout_duration, default, func, *args, **kwargs):
    """
    This function will spwan a thread and run the given function using the args, kwargs and 
    return the given default value if the timeout_duration is exceeded 
    """
    
    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = default
        def run(self):
            try:
                self.result = func(*args, **kwargs)
            except:
                self.result = 'Error'
                
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.is_alive():
        return default
    
    assert not it.result == 'Error', 'HPPT Error 403 or another block'
    return it.result    


def get_string_language(text: str, confidence=90):
    """
    Gets string and confidence: min per cent of major language
    Return major language or None if there is no language 
    with such confidence or encoding error
    """

    text = text.encode('utf_8', errors='ignore')
    text = text.decode('utf_8', errors='ignore')

    try:
        for language in Detector(text, quiet=True).languages:
            if language.confidence >= confidence:
                return language.code
    except Exception:
        #         print('!!!error encoding to utf_8!!!')
        pass

    return None


def get_string_size(text: str, encode='utf-8'):
    """
    Get string and encode 
    Return kb size of encoded string (encode could be None)
    """

    if encode:
        text = text.encode(encode, errors='ignore')

    size = getsizeof(text) / 1024

    return size


class Link:
    def __init__(self, url, title, info, date):
        self.url = url
        self.title = title
        self.info = info
        self.date = date
        self.data = None

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.url == other.url
        return NotImplemented

    def __hash__(self):
        return hash(self.url)

    def __str__(self):
        print('url: ', self.url, '\ntitle: ', self.title,
              '\ndate: ', self.date, '\ninfo: ', self.info, '\nscraped: ',
              self.data, '\n')
        return '\n'

    def scrape(self, driver, save, extract='ArticleSentencesExtractor', process=True):
        """
        Main function that scrapes google links 
        Main function that scrapes google links 
        Main function that scrapes google links  
        Scrapes self.url and returns the result to self.data
        """
#         print('\nstart scraping')

        if extract == 'ArticleSentencesExtractor':
            extractor = extractors.ArticleSentencesExtractor()
        elif extract == 'ArticleExtractor':
            extractor = extractors.ArticleExtractor()
        else:
            assert False, '!!!Extracter is False!!!'

#         print('\nextractor ready')

        content = None

        try:

#             print('\nget url: ', self.url)

            content = timeout(15, None, extractor.get_content_from_url, self.url)
        except:

#             print('\nusing driver')

            try:
                driver.get(self.url)
                html = timeout(15, None, driver.execute_script,
                                           "return document.documentElement.innerHTML")

#                 print('\nhtml: ', html)
                if html:
                    content = timeout(15, None, extractor.get_content, html)
            except Exception as error:
                print(error)        # unknown errors (rare)

        if not content:
            return None

#         print('\ncontent extracted:', content.encode('utf-8', errors='ignore'))

        examine = get_string_size(content) > MIN_SCRAPED_SIZE
        
#         print('size examined')
        
        if SCRAPED_LANGUAGE:
            examine &= (get_string_language(content) == SCRAPED_LANGUAGE)

#         print('language examined')    

#         print('\ncontent examined: ', examine)

        if examine:
            if process:
                content = process_text(content)
            if save:
                self.data = content  # could add saving if bad content
            return content

        return None


def get_driver_url_soup(driver, url=None):
    """
    Gets soup from driver url
    If you give no url then current html is scraped
    """

    if url:
        driver.get(url)
    html = driver.execute_script("return document.documentElement.innerHTML")
    soup = BeautifulSoup(html, features='lxml')

    return soup


def check_soup_recaptcha(soup) -> bool:
    """
    Checks google page for recaptcha
    """

    if soup.find_all('form', id='captcha-form'):
        #         print('!!!lol there is captcha!!!')
        return True

    return False


def check_soup_didnotmatch(soup) -> bool:
    """
    Checks google page for no result match
    """

    if re.findall('did not match', str(soup.find_all('div', id='topstuff'))):
        #         print('!!!did not match!!!')
        return True

    return False


def solve_recaptcha(driver, timer=0):
    """
    Gets anti-recaptcha driver with recaptcha 
    (driver.get() was already used and there is recaptcha)
    Solves recaptcha and returnes the current soup 
    """

    if timer >= 900:
        assert False, '!!!recaptcha failed many times!!!'

    curr_soup = get_driver_url_soup(driver)
    if not check_soup_recaptcha(curr_soup):
        return curr_soup

    curr_timer = 0
    while curr_timer < 300:
    
        if driver.current_url == 'https://www.google.com/sorry/index':
            assert False, '!!!you were caught by recaptcha infinitive loop, clean your ' \
                      'cookies, wait some time or change your IP!!!'

        curr_timer += 30
        time.sleep(30)
        #         element_present = EC.presence_of_element_located((By.CSS_SELECTOR, '.antigate_solver.recaptcha.in_process'))
        #         WebDriverWait(driver, 120, .02).until(element_present)     # can't see it, don't khow why

        soup = get_driver_url_soup(driver)
        if not check_soup_recaptcha(soup):
            return soup

    print('!!!anticaptcha failed, another try!!!')
    driver.refresh()

    return solve_recaptcha(driver, timer + curr_timer)


def scrape_gpage_links(soup, process=None) -> set:
    """
    Makes a set of Link objects from Google search page's BeautifulSoup()
    Each Link object has url, title, date and info
    """

    if process is None:
        process = {'title': False, 'info': False, 'date': True}
    link_set = set()
    upper_classes = soup.find_all('div', class_='gG0TJc')

    for single_class in upper_classes:

        url = single_class.find_all('a', class_="l lLrAF")[0]['href']
        title = single_class.find_all('a', class_="l lLrAF")[0].getText()
        info = single_class.find_all('div', class_="st")[0].getText()
        date = single_class.find_all('span', class_="f nsa fwzPFf")[0].getText()

        if process['title']:
            title = process_text(title)
        if process['info']:
            info = process_text(info)
        if process['date']:
            date = process_date(date)

        l = Link(url, title, info, date)
        # print(l, '\n\n\n')
        link_set.add(l)

    return link_set


def scrape_gsearch(obj, process=None, delete_previous=True):
    """
    Main function that scrapes Google search pages
    Gets Gsearch object, scrapes Gsearch.url into Gsearch.link_set
    If you don't have anti-captcha key change 497 to driver=run_chromedriver() 
    """

    if process is None:
        process = {'title': False, 'info': False, 'date': True}
    if obj.link_set:
        if delete_previous:
            print('!!!previous link set had been deleted!!!')
            obj.link_set = set()
        else:
            print('!!!new links will be added to previous link set!!!')

    assert (len(obj.number) == len(obj.query)) or len(obj.number) == 1, (
        '!!!length of queries and links numbers for them are not equal!!!')
    if len(obj.number) == 1:
        obj.number = obj.number * len(obj.query)
    driver = run_chromedriver() # if you have no ANTICAPTCHA_API_KEY
#     driver = run_anticaptcha_chromedriver(ANTICAPTCHA_API_KEY, ANTICAPTCHA_PLUGIN_PATH)
    for idx, query in enumerate(obj.query):

        links_per_gpages, gpages = get_link_per_gpage(obj.number[idx])
        obj.set_url_key('not needed', query, 'query')
        obj.set_url_key('num', str(links_per_gpages), 'num')

        for page in range(gpages):
            obj.set_url_key('start', str(page * links_per_gpages), 'num')

            soup = get_driver_url_soup(driver, obj.url)

            if check_soup_recaptcha(soup):
                soup = solve_recaptcha(driver)

            if check_soup_didnotmatch(soup):
                break

            obj.link_set |= scrape_gpage_links(soup, process)
    
    print('link set length: ', len(obj.link_set))
    driver.quit()


def scrape_link_set(obj, save=True, dump=False, path=None, amount=None, process=False):
    """
    Main function that scrapes Links set (Gsearch.link_set)
    Gets Gsearch object and scrapes Gsearch.link_set
    // Gsearch.link_set == {Link1, Link2, Link3, ...}
    Saves it to Link.data and dumps it to the path
    """

    if not save and not dump:
        print("!!!function does nothing, no dump, no save!!!")
        return None
    if path and not dump:
        print("!dump should be True if path given!")
    if amount == None:
        amount = len(obj.link_set)
    assert obj.link_set, "link set should be not empty"

    if dump:
        assert path != None, "path should be given"
        directory = os.path.join(path,
                 make_filename_safe(', '.join([re.sub(r'\+', ' ', query) for query in obj.query])))
        create_new_folder(directory)

    driver = run_chromedriver()
    bad_scrapes = 0
    set_subset = get_set_subset(obj.link_set, amount)

    for link in set_subset:

        if save and link.data:
            save = False

        result = link.scrape(driver, save=save, process=process)
        if result:
            if dump:
                f = open(os.path.join(directory, make_filename_safe(link.title) + '.txt'),
                         'w', encoding="utf-8")
                #                 f.write(str(link.url) + '\n\n')
                f.write(result)
                f.close()
        else:
            bad_scrapes += 1

    driver.quit()  # it is -repeats, -no result match, -scrape filter
    print(len(set_subset) - bad_scrapes, '  >', MIN_SCRAPED_SIZE, 'kb ',
          SCRAPED_LANGUAGE, 'language links are scraped\n')


class Gsearch:
    def __init__(self, query, links_number=0):
        """links_number=0 means all links from gsearch"""
        self.query = [re.sub(' ', '+', query) for query in to_list(query)]
        self.number = to_list(links_number)  # max ~350
        self.url = 'https://www.google.com/search?q='
        self.link_set = set()

    def __str__(self):
        print('query: ', self.query,  # '\nurl', self.url,
              '\nlinks: ', len(self.link_set), end='')
        return '\n'

    def set_url_key(self, key: str, value: str, pattern: str):
        """ 
        Adds features to self.url 
        pattern could be 'query', 'num', 'word'
        (tbm, nws, word); (tbm, isch, word); (source, lnms, word);
        (hl, en, word); (cr, countryUS, word); (start, 20, num);
        (num, 100, num);
        """
        if pattern == 'query':
            indificator = r'\?q=[\w+"\-%0-9]*'
            replacement = r'?q=' + value
        else:
            replacement = '&' + key + '=' + value
            if pattern == 'word':
                indificator = r'&' + key + r'=[\w]+'
            else:
                indificator = r'&' + key + r'=[0-9]+'
        if re.findall(indificator, self.url):
            self.url = re.sub(indificator, replacement, self.url)
        else:
            self.url = self.url + replacement

    def get_link_set(self, print=False, amount=None):

        if not self.link_set:
            assert False, "No links parsed (use scrape_gsearch())"
        if amount == None:
            return self.link_set
        if amount > len(self.link_set):
            print('!amount is larger than the link_set!')
            return self.link_set
        assert amount > 0, "amount should more than zero"

        subset = get_set_subset(self.link_set, amount)
        if print:
            for l in subset:
                print(l)
        return subset


def scrape_query_news_articles(queries, links_num, path=QUERIES_PATH, save=False):
    """
    Scrapes articles for every query from Google search news in english 
    Saves them into the object then dumps them into the path
    Returns Gsearch
    """

    search_obj = Gsearch(queries, links_num)
    search_obj.set_url_key('source', 'lnms', 'word')
    search_obj.set_url_key('tbm', 'nws', 'word')
    search_obj.set_url_key('hl', 'en', 'word')

    scrape_gsearch(search_obj)
    #     print(search_obj)

    scrape_link_set(search_obj, save=save, dump=True, path=path)
    
    return Gsearch
    
  
# scrape_query_news_articles('agriculture', 100)
# scrape_query_news_articles(['bitcoin', 'zimbocash', 'ethereum'], [100, 50, 100])
