import time
import csv
import requests
from neo4j import GraphDatabase
from bs4 import BeautifulSoup
import pyuser_agent


class TopicData:
    def __init__(self, topic):
        self.topic = topic

    def get_topic_page_count(self):
        ua = pyuser_agent.UA()
        headers = {
          'User-Agent': ua.random,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate, br',
          'Connection': 'keep-alive',
        }

        response = requests.get(f'https://github.com/topics/{self.topic}?page=1', headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        try:
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
        except Exception as e:
            print('Nothing found')
            return 0, 0


class BuildDatabase:
    def __init__(self):
        driver = GraphDatabase.driver("neo4j://neo4j:7687", auth=("neo4j", "dcentn"))
        self.driver = driver

    def update_neo4j_data(self, t):
        filename = f'/usr/src/app/reports/github_topic_contributors_crypto_1645926345.csv'
        print(filename)
        with open(filename, 'r') as file:
            reader = csv.reader(file)
            for each_row in reader:
                topic = each_row[0]
                name_of_org = each_row[1]
                name_of_project = each_row[2]
                url_of_project = each_row[3]
                contributor = each_row[4]
                url_of_contributor = each_row[5]

                with self.driver.session() as session:
                    session.write_transaction(
                        self.add_data,
                        topic,
                        name_of_org,
                        name_of_project,
                        url_of_project,
                        contributor,
                        url_of_contributor
                    )

                time.sleep(1)

            self.driver.close()

    @staticmethod
    def add_data(
        tx,
        topic,
        name_of_org,
        name_of_project,
        url_of_project,
        contributor,
        url_of_contributor
    ):
        tx.run("MERGE (o:Organization {name: $org_name}) "
               "MERGE (o)<-[:PROJECT]-(p:Project {name: $project_name, url: $project_url}) "
               "MERGE (p)<-[:CONTRIBUTOR]-(c:Contributor {name: $contributor_name, url: $contributor_url})",
               org_name=name_of_org,
               project_name=name_of_project,
               project_url=url_of_project,
               contributor_name=contributor,
               contributor_url=url_of_contributor
               )

    @staticmethod
    def add_friend(tx, name, friend_name):
        tx.run("MERGE (a:Person {name: $name}) "
               "MERGE (a)-[:KNOWS]->(friend:Person {name: $friend_name})",
               name=name, friend_name=friend_name)

    def process_report(self):
        self.update_neo4j_data("crypto")

        # with self.driver.session() as session:
        #     session.write_transaction(self.add_friend, "Arthur", "Guinevere")
        #     session.write_transaction(self.add_friend, "Arthur", "Lancelot")
        #     session.write_transaction(self.add_friend, "Arthur", "Merlin")

        #self.driver.close()
