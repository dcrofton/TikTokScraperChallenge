from selenium import webdriver
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import os
import time
import re
import csv

fashion_url = 'https://www.tiktok.com/tag/fashion'

# Set the path of the Firefox binary
firefox_binary_path = "/usr/bin/firefox-esr"

keywords = ['clothes', 'outfit', 'style']
score_weights = [5, 15, 15, 25, 25, 15]
fieldnames = ['Post URL','Account','Likes', 'Saved', 
              'Caption', 'Hashtags', 'Date Posted', 'Date Collected']

#Account for no keywords being found in account name, captions, or hashtags
post_score_max = [1,0,0,1,1,10000]

date_pattern = re.compile(r'\d{4}-\d{1,2}-\d{1,2}|\d{1,2}-\d{1,2}|\d+d ago')
days_ago_pattern = re.compile(r'\d+d ago|\d+h ago|\d+m ago|\d+s ago')
today_date = (date.today()).strftime("%m/%d/%Y")

def get_driver():
    # Create the Firefox driver
    options = webdriver.FirefoxOptions()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = firefox_binary_path

    # Set the display port as an environment variable
    display_port = os.environ.get("DISPLAY_PORT", "99")
    display = f":{display_port}"
    os.environ["DISPLAY"] = display

    # Start the Xvfb server
    xvfb_cmd = f"Xvfb {display} -screen 0 1024x768x24 -nolisten tcp &"
    os.system(xvfb_cmd)

    driver = webdriver.Firefox(options=options)
    return driver

def convert_to_numeric(value_str):
    # Convert "M" to million
    if value_str.endswith("M"):
        return int(float(value_str[:-1]) * 1e6)
    # Convert "K" to thousand
    elif value_str.endswith("K"):
        return int(float(value_str[:-1]) * 1e3)
    # No conversion needed
    else:
        return int(value_str)

def scrape_post(driver, post_url):
    return_data = None
    driver.get(post_url)
    object_score = [0,0,0,0,0,0]
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    content = BeautifulSoup(driver.page_source, "lxml")
    account = content.find('span', attrs={"class": 'tiktok-1c7urt-SpanUniqueId evv7pft1'})
    like_count = content.find('strong', attrs={"data-e2e": 'like-count'})
    saved_count = content.find('strong', attrs={"data-e2e": 'undefined-count'})
    date_posted = ""
    for tag in content.find_all(attrs={"class": 'tiktok-31630c-DivInfoContainer e17fzhrb0'}):
        for component in tag:
            text = component.text.split(' · ')[-1]
            if len(text) != 0 and text != "Follow":
                if bool(days_ago_pattern.match(text)):
                    days_to_subtract = int(text.split('d')[0])
                    date_posted = datetime.now() - timedelta(days=days_to_subtract)
                    date_posted = date_posted.strftime("%m/%d/%Y")
                else:
                    nums = text.split('-')
                    if len(nums) == 2:
                        date_posted = "{m}/{d}/2023".format(m=nums[0], d=nums[1])
                    if len(nums) == 3:
                        date_posted = "{m}/{d}/{y}".format(m=nums[1], d=nums[2], y=nums[0])
    caption = ""
    hashtags = ""
    for tag in content.find_all(attrs={"class": ['tiktok-j2a19r-SpanText efbd9f0', 
                                                    'ejg0rhn6 tiktok-g8ml1x-StyledLink-StyledCommonLink er1vbsz0']}):
        if tag.text != " ":
            caption = caption + tag.text
        if '#' in tag.text:
            hashtags = hashtags + tag.text
    if account != None and like_count != None and saved_count != None and date_posted != '':
        num_like_count = convert_to_numeric(like_count.text)
        object_score[1] = num_like_count
        if num_like_count > post_score_max[1]:
            post_score_max[1] = num_like_count
        num_saved_count = convert_to_numeric(saved_count.text)
        object_score[2] = num_saved_count
        if num_saved_count > post_score_max[2]:
            post_score_max[2] = num_saved_count
        days_difference = (datetime.strptime(today_date, "%m/%d/%Y") - datetime.strptime(date_posted, "%m/%d/%Y")).days
        object_score[5] = days_difference
        if days_difference < post_score_max[5]:
            post_score_max[5] = days_difference
        keywords_in_account = 0
        keywords_in_caption = 0
        keywords_in_hashtags = 0
        for keyword in keywords:
            if keyword in account:
                keywords_in_account += 1
            if keyword in caption:
                keywords_in_caption += 1
            if keyword in hashtags:
                keywords_in_hashtags += 1
        object_score[0] = keywords_in_account
        object_score[3] = keywords_in_caption
        object_score[4] = keywords_in_hashtags
        if keywords_in_account > post_score_max[0]:
            post_score_max[0] = keywords_in_account
        if keywords_in_caption > post_score_max[3]:
            post_score_max[3] = keywords_in_caption
        if keywords_in_hashtags > post_score_max[4]:
            post_score_max[4] = keywords_in_hashtags
        return_data = {
            'Post URL': post_url,
            'Account': account.text,
            'Likes': like_count.text,
            'Saved': saved_count.text,
            'Caption': caption,
            'Hashtags': hashtags,
            'Date Posted': date_posted,
            'Date Collected': today_date,
            'Score': object_score
        }
    return return_data

def get_urls(driver):
    driver.get(fashion_url)
    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
    content = BeautifulSoup(driver.page_source, "lxml")
    urls = []
    for post in content.find_all('div', attrs={"class": 'tiktok-1as5cen-DivWrapper e1cg0wnj1'}):
        for tag in post:
            if tag.has_attr("href"):
                if len(tag['href']) != 0:
                    urls.append(tag['href'])
    print(len(urls))
    return urls

def get_post_results(driver, post_urls):
    post_results = []
    for post_url in post_urls:
        post_data = scrape_post(driver, post_url)
        if post_data != None:
            post_results.append(post_data)
    return post_results

def get_score(score_array):
    return ((score_array[0]/post_score_max[0])*score_weights[0] + (score_array[1]/post_score_max[1])*score_weights[1] + 
            (score_array[2]/post_score_max[2])*score_weights[2] + (score_array[3]/post_score_max[3])*score_weights[3] +
            (score_array[4]/post_score_max[4])*score_weights[4] + (post_score_max[5]/score_array[5])*score_weights[5])

def set_score(post_results):
    number_of_posts = len(post_results)
    for i in range(number_of_posts):
        post_results[i]['Score'] = get_score(post_results[i]['Score'])

def sort_post_results(post_results, key):
    post_results.sort(key=lambda x:x[key], reverse=True)

#Used locally to create csv file of results
def create_csv(title, number_to_save, post_results):  
    with open('TikTokFashionData.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(fieldnames)
        for post in post_results[:number_to_save]:
            writer.writerow(post.values())

#Used with docker
def print_post_results(post_results, print_number_of_posts_sampled):
    for post in post_results:
        print(post)
    if (print_number_of_posts_sampled):
        print(len(post_results))

def main():
    driver = get_driver()
    post_urls = get_urls(driver)
    post_results = get_post_results(driver, post_urls)
    set_score(post_results)
    sort_post_results(post_results, 'Score')
    print_post_results(post_results, True)
    driver.quit()

if __name__ == "__main__":
    main()