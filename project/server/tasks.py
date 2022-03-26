import os
import time
import csv
import json
import redis
import datetime

from celery import Celery
from celery.utils.log import get_task_logger

import random
import requests
from bs4 import BeautifulSoup
import pyuser_agent

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
logger = get_task_logger(__name__)

api_key = os.environ.get("SCRAPER_API_KEY")
db = redis.Redis(host='redis', port=6379, db=0)  # connect to server


def get_topic_page_count(topic):
    ua = pyuser_agent.UA()
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    response = requests.get(f'https://github.com/topics/{topic}?page=1', headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    pages_f = int(
        soup.select_one('span[class="select-menu-item-text d-flex flex-justify-between"] span').text.strip().replace(
            ',',
            ''))

    if pages_f < 1020:
        pages = round(pages_f / 30)
    else:
        pages = 35

    if pages == 0:
        pages = 1

    return pages_f, pages


def get_all_projects(pages, _topic):
    _all_articles_frames = []

    for page in range(1, pages + 1):
        try:
            soup = get_soup_for_topic_projects(page, _topic)
            articles = soup.find_all('article', {'class': 'border rounded color-shadow-small color-bg-subtle my-4'})

            article_dict = {}
            _master_list = []
            for article in articles:
                _article_data = article.find('h3').findAll('a')

                article_dict['Name_of_org'] = _article_data[0].text.rstrip().lstrip().replace('\n',
                                                                                              '').rstrip().lstrip()
                article_dict['URL_of_org'] = 'https://github.com' + _article_data[0]['href'].rstrip().lstrip()

                article_dict['Name_of_project'] = _article_data[1].text.rstrip().lstrip().replace('\n',
                                                                                                  '').rstrip().lstrip()
                article_dict['URL_of_project'] = 'https://github.com' + _article_data[1]['href'].rstrip().lstrip()

                article_dict['Contributors_URL'] = article_dict['URL_of_project'] + '/graphs/contributors-data'

                _master_list.append(article_dict.copy())

            # REDIS CASH #
            field = f'{_topic}_{page}'
            value = json.dumps(_master_list)
            db.set(field, value, ex=86400)  # ttl 2 hours

            # add delay to the crawl. random is used to vary crawl delay
            logger.info(f'project page {page}')
            time.sleep(random.randint(1, 3))

        except Exception as e:
            print('Error ', e)
            print(f'Error getting articles of Page {page} of {pages}')


def get_soup_for_topic_projects(page, _topic):
    ua = pyuser_agent.UA()
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',

    }
    url = f'https://github.com/topics/{_topic}?page={page}'
    payload = {'api_key': api_key, 'url': url, 'keep_headers': 'true'}
    response = requests.get('http://api.scraperapi.com', params=payload, headers=headers)
    if response.status_code == 200:
        return BeautifulSoup(response.text, 'html.parser')
    else:
        return None


def get_data_for_contributors(url):
    global reTry_counter
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0',

    }
    payload = {'api_key': api_key, 'url': url, 'keep_headers': 'true'}
    response = requests.get('http://api.scraperapi.com', params=payload, headers=headers)

    if response.status_code == 200:
        print('successful json data')
        reTry_counter = 0
        return response.json()

    else:
        print('Error in getting data for url: ', url, '\t', response.status_code, '<========')
        return None

    # else:
    #     print('Error in getting data for url: ', url, '\t', response.status_code, '<========')
    #     if reTry_counter < 10:
    #         time.sleep(3)
    #         reTry_counter = + 1
    #         return get_data_for_contributors(url)
    #
    #     else:
    #         return None


def get_contributors_for_topic_project(_project, _url):
    _contributors_data = get_data_for_contributors(_url)
    _contributors_list = []
    _final_contributors_dict = {'Project': _project}

    if _contributors_data is None:
        return None

    for _ in _contributors_data:
        _project_contributors_dict = {
            'Contributor': _['author']['login'],
            'Contributor_Account_URL': 'https://github.com' + _['author']['path']
        }

        _contributors_list.append(_project_contributors_dict.copy())

    _final_contributors_dict['Contributors'] = _contributors_list

    return _final_contributors_dict


def get_all_articles(pages, _topic):
    _all_articles_frames = []

    for page in range(1, pages + 1):
        try:
            time.sleep(random.randint(1, 3))
            soup = get_soup_for_topic_projects(page, _topic)
            if soup is not None:
                _temp_articles = get_articles_for_topic_projects_per_page(soup)
                _all_articles_frames.append(_temp_articles)
            else:
                print(f'Error getting articles of Page {page} of {pages}')

        except Exception as e:
            print('Error ', e)
            print(f'Error getting articles of Page {page} of {pages}')
            return _all_articles_frames

    return _all_articles_frames


def build_file(topic):
    absolute_path = os.path.dirname(os.path.abspath(__file__))

    timestamp = datetime.datetime.now().timestamp()
    filename = absolute_path + f'/reports/github_topic_contributors_{topic}_{int(round(timestamp))}.csv'

    headers = ['Name of topic', 'Name of org', 'Name of project', 'Url of project', 'Name of contributor',
               'Url of contributor']

    with open(filename, 'a+', newline='') as f:
        write = csv.writer(f)
        write.writerow(headers)

        keys = f'{topic}_*'
        all_keys = db.keys(keys)

        # each iteration is a page - update spreadsheet with each page
        for k in all_keys:
            master_matched_list_r = []
            value = db.get(k)
            j = json.loads(value)

            logger.info(f'get contributors {k}')

            # iterate through each page - each iteration is a project
            for _project in j:
                _contributors_url = _project["Contributors_URL"]
                _contributors_dict = get_contributors_for_topic_project(_project, _contributors_url)

                if _contributors_dict is not None:
                    # loop through contributors
                    for _contributor in _contributors_dict["Contributors"]:
                        temp_ = [
                            topic,
                            _project["Name_of_org"],
                            _project["Name_of_project"],
                            _project["URL_of_project"],
                            _contributor["Contributor"],
                            _contributor["Contributor_Account_URL"]
                        ]
                        master_matched_list_r.append(temp_)

                # add delay to the crawl. random is used to vary crawl delay
                time.sleep(random.randint(1, 2))
            # write all contributors to a project to spreadsheet
            write.writerows(master_matched_list_r)


def build_contributor_file(topic):
    absolute_path = os.path.dirname(os.path.abspath(__file__))

    timestamp = datetime.datetime.now().timestamp()
    # filename = absolute_path + f'/reports/github_contributors_{topic}_{int(round(timestamp))}.csv'
    filename = absolute_path + f'/reports/github_contributors_{int(round(timestamp))}.csv'

    headers = ['Name of topic', 'Name of org', 'URL of org', 'Name of project', 'Url of project', 'Contributor',
               'Url of contributor', 'Name', 'Additional Name', 'Website', 'Home Location', 'Works For', 'Email',
               'Twitter Link', 'Twitter Handle']

    with open(filename, 'a+', newline='') as f:
        write = csv.writer(f)
        write.writerow(headers)

        keys = f'contributor_*'
        all_keys = db.keys(keys)

        # each iteration is a page - update spreadsheet with each page
        for k in all_keys:
            master_matched_list_r = []
            value = db.get(k)
            _contributor = json.loads(value)

            temp_ = [
                topic,
                _contributor["Name_of_org"],
                _contributor["URL_of_org"],
                _contributor["Name_of_project"],
                _contributor["URL_of_project"],
                _contributor["Contributor"],
                _contributor["Contributor_URL"],
                _contributor["Name"],
                _contributor["Additional_Name"],
                _contributor["Website"],
                _contributor["Home_Location"],
                _contributor["Works_For"],
                _contributor["Email"],
                _contributor["Twitter_Link"],
                _contributor["Twitter_Handle"],
            ]

            logger.info(f'write record: {k}')
            write.writerow(temp_)

            #master_matched_list_r.append(temp_)
            #write.writerow(master_matched_list_r)

            # add delay to the crawl. random is used to vary crawl delay
            #time.sleep(random.randint(1, 2))

        # write all contributors to a spreadsheet
        #write.writerows(master_matched_list_r)


def get_contributor_details(url):
    _contributor_details = {
        "Name": "",
        "Additional_Name": "",
        "Website": "",
        "Home_Location": "",
        "Works_For": "",
        "Email": "",
        "Twitter_Link": "",
        "Twitter_Handle": ""}

    try:
        ua = pyuser_agent.UA()

        headers = {
            'User-Agent': ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

        payload = {'api_key': api_key, 'url': url, 'keep_headers': 'true'}
        response = requests.get('http://api.scraperapi.com', params=payload, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            name_data = soup.find('h1', class_="vcard-names")
            if name_data is not None:
                for _span in name_data.find_all("span"):
                    _t = _span["itemprop"]
                    if _t == "name":
                        _contributor_details["Name"] = _span.text.replace('\n', '').replace('  ', '')
                    if _t == "additionalName":
                        _contributor_details["Additional_Name"] = _span.text.replace('\n', '').replace('  ', '')

            data = soup.find('ul', class_="vcard-details")
            if data is not None:
                for _li in data.find_all("li"):
                    _t = _li["itemprop"]
                    if _t == "url":
                        _href = _li.find('a')
                        _contributor_details["Website"] = _href["href"]
                    if _t == "homeLocation":
                        _contributor_details["Home_Location"] = _li["aria-label"].replace('Home location: ', '')
                    if _t == "worksFor":
                        _contributor_details["Works_For"] = _li["aria-label"].replace('Organization: ', '')
                    if _t == "email":
                        _contributor_details["Email"] = _li["aria-label"]
                    if _t == "twitter":
                        _href = _li.find('a')
                        _contributor_details["Twitter_Link"] = _href["href"]
                        _contributor_details["Twitter_Handle"] = _href.text.replace('\n', '').replace('  ', '')

            logger.info("process..")
            return _contributor_details

        else:
            logger.info(f'###########################')
            logger.info(f'Bad crawl')
            logger.info(response.status_code)
            logger.info(response.text)
            logger.info(url)
            logger.info(f'###########################')

            return None

    except Exception as e:
        print('Error ', e)
        print(f'Error getting contributors')

        return None


def process_contributor_file(topic):
    _contributor_list = []

    filename = f'/usr/src/app/reports/github_topic_contributors_crypto_1647446085.csv'
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        row = 0
        for each_row in reader:
            contributor_dict = {}
            topic = each_row[0]
            contributor_dict['Name_of_org'] = each_row[1]
            contributor_dict['URL_of_org'] = 'https:github.com/' + each_row[1]
            contributor_dict['Name_of_project'] = each_row[2]
            contributor_dict['URL_of_project'] = each_row[3]
            contributor_dict['Contributor'] = each_row[4]
            contributor_dict['Contributor_URL'] = each_row[5]

            _contributor = get_contributor_details(each_row[5])
            if _contributor is None:
                continue

            contributor_dict.update(_contributor)

            # REDIS CASH #
            field = f'contributor_{row}'
            value = json.dumps(contributor_dict)
            db.set(field, value, ex=86400)  # ttl 24 hours

            logger.info(field)
            row += 1

            # if row == 50:
            #     return

            time.sleep(random.randint(1, 3))


@celery.task(name="project_task")
def project_task(topic):
    pages_f, pages = get_topic_page_count(topic)
    mes = 'Total Listings Found ' + str(pages_f) + '; Pages ' + str(pages)
    logger.info(mes)

    # build projects and add to redis cache
    get_all_projects(pages, topic)  # TODO: LIMIT TO 5 PAGES AT A TIME

    # get contributors and add project to spreadsheet
    build_file(topic)

    return "Report Ready"


@celery.task(name="contributor_task")
def contributor_task(topic):
    # from file, crawl contributor ad add to redis
    process_contributor_file(topic)

    # pull from redis and add to a new file
    build_contributor_file("crypto")

    return "Report Ready"
