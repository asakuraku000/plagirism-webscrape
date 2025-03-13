import requests
from flask_cors import CORS
import os
import urllib
from requests_html import HTML
from requests_html import HTMLSession
from flask import Flask, request, render_template

app = Flask(__name__)
CORS(app, supports_credentials=True)

@app.route('/')
def index():

  cls()
  output = ""
  try:
    search = request.args.get("data")
    search = search.split(".")
    output = []
    for i in search:
      i = i.split("\n")
      for j in i:
        results = google_search(j)
        for k in results:
          output.append(k)
  except:
    output = ""
  return output


def get_source(url):
  try:
    session = HTMLSession()
    response = session.get(url)
    return response

  except requests.exceptions.RequestException as e:
    print(e)


def scrape_google(query):
  query = urllib.parse.quote_plus(query)
  response = get_source("https://www.google.co.uk/search?q=" + query)

  links = list(response.html.absolute_links)
  google_domains = ('https://www.google.', 'https://google.',
                    'https://webcache.googleusercontent.',
                    'http://webcache.googleusercontent.',
                    'https://policies.google.', 'https://support.google.',
                    'https://maps.google.')

  for url in links[:]:
    if url.startswith(google_domains):
      links.remove(url)

  return links


def get_results(query):

  query = urllib.parse.quote_plus(query)
  response = get_source("https://www.google.co.uk/search?q=" + query)

  return response


def parse_results(response):
  try:
    css_identifier_result = ".tF2Cxc"
    css_identifier_title = "h3"
    css_identifier_link = ".yuRUbf a"
    css_identifier_text = ".VwiC3b"
    results = response.html.find(css_identifier_result)

    output = []

    for result in results:

      item = {
        'title': result.find(css_identifier_title, first=True).text,
        'link': result.find(css_identifier_link, first=True).attrs['href'],
        'text': result.find(css_identifier_text, first=True).text
      }

      output.append(item)

    return output
  except:
    return []


def google_search(query):
  response = get_results(query)
  return parse_results(response)

def cls():
    os.system('cls' if os.name=='nt' else 'clear')

app.run(debug=False)
