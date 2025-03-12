import time
from collections import namedtuple
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util


driver = None


# Define the data structure for storing dataset information
Dataset = namedtuple("Dataset", "name, url, description, source,score")

# Define the Kaggle data portal

Dataportal = namedtuple(
    "Dataportal", "name, query_url, title_element, url_element, description"
)
kaggle = Dataportal(
    "Kaggle",
    "https://www.kaggle.com/datasets?search=[QUERY]",
    "/html/body/main/div[1]/div/div[5]/div[2]/div[5]/div/div/div/ul/li",
    ".//a",
    [
        "/html/body/main/div[1]/div/div[5]/div[2]/div/div[2]/div/div[6]/div[1]/div[1]/div[2]/div/div/div",
        "/html/body/main/div[1]/div/div[5]/div[2]/div/div[2]/div/div[5]/div[1]/div[1]/div[2]/div/div/div",
    ],
)
datagov = Dataportal(
    "Data.gov",
    "https://catalog.data.gov/dataset?q=[QUERY]",
    "/html/body/div[2]/div/div[2]/div/section[1]/div[2]/ul/li/div/h3/a",
    "/html/body/div[2]/div/div[2]/div/section[1]/div[2]/ul/li/div/h3/a",
    "/html/body/div[2]/div/div[2]/div/article/section[1]/div[2]",
)
eu = Dataportal(
    "EU Portal",
    "https://data.europa.eu/data/datasets?query=[QUERY]&locale=en",
    "./div/div/div[1]/div[1]/h2",
    "/html/body/div/div[3]/div[2]/div/div[1]/section/a",
    "/html/body/div/div[3]/div[2]/div/div[2]/div[2]/div[1]/div[1]/div/div",
)

# Assessments functinon using hugging face transformers. the model name parameter can be change to other hugging face transformers models
def get_scores_transformer(a,b,model_name="sentence-transformers/distiluse-base-multilingual-cased-v1",
):
    model = SentenceTransformer(model_name)
    embeddings = model.encode([sentence1, sentence2])
    similarity_score = util.cos_sim(embeddings[0], embeddings[1])
    return similarity_score.item()


def get_scores_TfidfVectorizer(a, b):

    # print("calculating similarty",a ,b)
    vect = TfidfVectorizer()
    corpus = [a, b]

    v = vect.fit_transform(corpus)
    # print("similarty is  ",cosine_similarity(v)[0,1])
    return cosine_similarity(v)[0, 1]


def init_driver():
    # Create a Firefox Options object
    global driver
    options = Options()

    # Set preferences to enforce English language
    options.set_preference("intl.accept_languages", "en-US, en")
    options.set_preference("intl.locale.requested", "en-US")

    # Set to headless if needed
    options.headless = True  # Running headless, set to False if you want a GUI

    # Initialize the WebDriver with the specified options
    driver = webdriver.Firefox(options=options)


def shutdown():
    global driver
    driver.quit()


def find_elements_with_fallback(driver, query, db, query_url_template):
    t1 = time.time()  # Start the timer
    max_fallbacks = len(query.split(";")) - 1
    fallback = 0
    elements = []

    while len(elements) == 0:  # Continue until elements are found
        elements = driver.find_elements(By.XPATH, query_url_template)
        if time.time() - t1 > 5:  # Check if no results found within 5 seconds
            if fallback < max_fallbacks:
                fallback += 1
                query = ";".join(
                    query.split(";")[:-1]
                )  # Remove one word from the query
                url = db.query_url.replace("[QUERY]", query)
                driver.get(url)
                time.sleep(2)  # Allow time for the page to load
                t1 = time.time()  # Reset the timer for the next iteration
            else:
                return []  # No results found after all fallbacks

    return elements  # Return the found elements


def scrape_kaggle(query, background, func):
    global driver
    # Replace placeholder in the URL with the actual query
    url = kaggle.query_url.replace("[QUERY]", query)
    driver.get(url)
    time.sleep(4)  # Wait for the page to load

    elements = find_elements_with_fallback(driver, query, kaggle, kaggle.title_element)
    if not len(elements):
        return elements
    # Find all elements matching the title_element XPath
    # elements = driver.find_elements(By.XPATH, kaggle.title_element)

    print(f"Found {len(elements)} elements")

    dataset_list = []
    for element in elements:
        # Get the link and its attributes
        link = element.find_element(By.XPATH, kaggle.url_element)
        aria_label = link.get_attribute("aria-label")
        href = link.get_attribute("href")

        # Open the link in a new window/tab
        driver.execute_script("window.open(arguments[0]);", href)
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(1)

        # Retrieve the description of the dataset
        descriptions = driver.find_elements(By.XPATH, kaggle.description[0])
        if not descriptions:
            descriptions = driver.find_elements(By.XPATH, kaggle.description[1])

        # Extract text from each paragraph within the description
        p_elements = descriptions[0].find_elements(By.TAG_NAME, "p")
        full_text = " ".join(p.text for p in p_elements)
        full_text = full_text.replace(
            "\u2015", "-"
        )  # Replace en-dash with hyphen if necessary

        score = func(query + " " + background, full_text + " " + aria_label)

        dataset_list.append(Dataset(aria_label, href, full_text, kaggle.name, score))

        # Close the current tab and switch back to the original tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    return dataset_list


def scrape_datagov(query, background, func):
    global driver
    # Replace placeholder in the URL with the actual query
    url = datagov.query_url.replace("[QUERY]", query)
    driver.get(url)

    time.sleep(3)  # Wait for the page to load

    elements = find_elements_with_fallback(
        driver, query, datagov, datagov.title_element
    )
    if not len(elements):
        return elements
    # Find all elements matching the title_element XPath
    # elements = driver.find_elements(By.XPATH, datagov.title_element)
    print(f"Found {len(elements)} elements")

    dataset_list = []
    for element in elements:

        # Get the link and its attributes
        aria_label = element.text
        href = element.get_attribute("href")
        # Open the link in a new window/tab
        driver.execute_script("window.open(arguments[0]);", href)
        WebDriverWait(driver, 30).until(
            lambda driver: driver.execute_script("return document.readyState")
            == "complete"
        )
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(6)

        # Retrieve the description of the dataset
        descriptions = driver.find_elements(By.XPATH, datagov.description)

        # Extract text from each paragraph within the description
        p_elements = descriptions[0].find_elements(By.TAG_NAME, "p")
        full_text = " ".join(p.text for p in p_elements)
        full_text = full_text.replace(
            "\u2015", "-"
        )  # Replace en-dash with hyphen if necessary
        full_text = full_text.replace(
            "\u2212", "-"
        )  # Replace en-dash with hyphen if necessary

        score = func(query + " " + background, full_text + " " + aria_label)

        dataset_list.append(Dataset(aria_label, href, full_text, datagov.name, score))

        # Close the current tab and switch back to the original tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
    return dataset_list


def scrape_eu(query, background, func):
    global driver
    # Replace placeholder in the URL with the actual query
    url = eu.query_url.replace("[QUERY]", query)
    driver.get(url)
    time.sleep(3)  # Wait for the page to load

    elements = find_elements_with_fallback(driver, query, eu, eu.url_element)
    if not len(elements):
        return elements
    # Find all elements matching the title_element XPath
    # elements = driver.find_elements(By.XPATH, eu.url_element)
    print(f"Found {len(elements)} elements")

    dataset_list = []
    for element in elements:
        h2_element = element.find_element(By.XPATH, eu.title_element)
        aria_label = h2_element.text

        href = element.get_attribute("href")
        # Open the link in a new window/tab
        driver.execute_script("window.open(arguments[0]);", href)

        driver.switch_to.window(driver.window_handles[1])
        time.sleep(6)

        # Retrieve the description of the dataset
        descriptions = driver.find_elements(By.XPATH, eu.description)

        # Extract text from each paragraph within the description
        p_elements = descriptions[0].find_elements(By.TAG_NAME, "p")
        full_text = " ".join(p.text for p in p_elements)
        full_text = full_text.replace(
            "\u2015", "-"
        )  # Replace en-dash with hyphen if necessary
        full_text = full_text.replace(
            "\u2212", "-"
        )  # Replace en-dash with hyphen if necessary

        score = func(query + " " + background, full_text + " " + aria_label)

        dataset_list.append(Dataset(aria_label, href, full_text, eu.name, score))
        # Close the current tab and switch back to the original tab
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    return dataset_list


# Main execution
if __name__ == "__main__":
    init_driver()

    # print(scrape_eu(driver, "machine learning", eu))
    query = "food"
    background = "food food food food"
    scraped = scrape_kaggle(query, background, get_scores_TfidfVectorizer)

    sentence1 = "This is foods"
    sentence2 = "This dataset contains food"

    similarity_score = get_scores_transformer(sentence1, sentence2)
    print("Similarity Score:", similarity_score)
