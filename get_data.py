import time
from collections import namedtuple
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sklearn.metrics.pairwise import cosine_similarity
#from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer

# Define data structures
Dataportal = namedtuple('Dataportal', 'name, query_url, title_element, url_element, source_element')
Dataset = namedtuple('Dataset', 'name, url, source, c_score')

# Define portals
eu = Dataportal('EU Portal', 'https://data.europa.eu/data/datasets?query=[QUERY]&locale=en', '/html/body/div/div[3]/div[2]/div/div[1]/section/a/div/div/div[1]/div[1]/h2', '/html/body/div/div[3]/div[2]/div/div[1]/section/a', '/html/body/div/div[3]/div[2]/div/div[1]/section/a/div/div/small/div[2]/span')
kaggle = Dataportal('Kaggle', 'https://www.kaggle.com/datasets?search=[QUERY]', '/html/body/main/div[1]/div/div[6]/div[6]/div/div/div/ul/li/div[1]/a/div[2]/div', '/html/body/main/div[1]/div/div[6]/div[6]/div/div/div/ul/li/div[1]/a', None)
datahub = Dataportal('Datahub', 'https://datahub.io/search?q=[QUERY]', '/html/body/section/div/div/div[1]/section[2]/div/div/div/div/div/div[1]/div[1]/a/h3', '/html/body/section/div/div/div[1]/section[2]/div/div/div/div/div/div[1]/div[1]/a', None)
datagov = Dataportal('Data.gov', 'https://catalog.data.gov/dataset?q=[QUERY]', '/html/body/div[2]/div/div[2]/div/section[1]/div[2]/ul/li/div/h3/a', '/html/body/div[2]/div/div[2]/div/section[1]/div[2]/ul/li/div/h3/a', '/html/body/div[2]/div/div[2]/div/section[1]/div[2]/ul/li/div/div[2]/p')

# Set path to firefox executable here
FF_PATH = r'C:\Program Files\Mozilla Firefox\firefox.exe'
driver = None

def init():
    global driver
    options = Options()
    options.headless = False
    binary = FirefoxBinary(FF_PATH)
    driver = webdriver.Firefox(options=options, firefox_binary=binary)

def get_scores(a, b):
    """
    Return cosine score from input a and b.
    In this use case, a is the background information (bg + query) and b is the dataset title.
    """
    vect = TfidfVectorizer()
    corpus = [a,b]
    v = vect.fit_transform(corpus)
    return cosine_similarity(v)[0,1]

def query(dp, query, bg):
    """
    Queries a data portal dp with a given query, then ranks results based on background information bg.
    Uses a fallback mechanism in case the search query doesn't match anything, in which case a new search is performed with one word less.
    """
    global driver
    url = dp.query_url.replace('[QUERY]', query)
    driver.get(url)
    time.sleep(2)
    t1 = round(time.time())
    max_fallbacks = len(query.split())-2
    fallback = 0
    l = 0
    while l==0:
        titles = driver.find_elements(By.XPATH, dp.title_element)
        l = len(titles)
        if round(time.time())-t1 > 5:    #no results found
            if max_fallbacks > 0 and fallback < max_fallbacks:    #fallbacks remaining, removing one keyword
                fallback = fallback + 1
                query = ' '.join(query.split()[:-1])
                url = dp.query_url.replace('[QUERY]', query)
                driver.get(url)
                time.sleep(2)
                t1 = round(time.time())
            else: return []
        time.sleep(1)
    titles = driver.find_elements(By.XPATH, dp.title_element)
    urls = driver.find_elements(By.XPATH, dp.url_element)
    if dp.source_element != None:
        sources = driver.find_elements(By.XPATH, dp.source_element)
    datasets = []
    for i in range(len(titles)):
        c_score = get_scores(bg+' '+query, titles[i].text)
        if dp.source_element == None:
            datasets.append(Dataset(titles[i].text, urls[i].get_attribute('href'), dp.name, c_score))
        else:
            datasets.append(Dataset(titles[i].text, urls[i].get_attribute('href'), dp.name+': '+sources[i].text, c_score))
    return datasets

def shutdown():
    global driver
    driver.quit()

if __name__ == '__main__':    # Can be used to test the functionality
    init()
    d = query(kaggle, 'food', 'fast food indian production')
    print(d)
    shutdown()