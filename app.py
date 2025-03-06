from flask import Flask
import math
import re
import requests
from collections import Counter
from googlesearch import search
from flask import request
from bs4 import BeautifulSoup
import os
import json

app = Flask(__name__)


@app.route('/')
def index():
    os.system('cls' if os.name == 'nt' else 'clear')
    query = request.args.get('data', default='*', type=str)
    neko = query
    '''if (len(query) >= 100):
        #query = query.replace("the", "")
        query = query.split(" ")
        key = ""
        for i in range(0, 40):
            key += query[i] + " "
        query = key'''
    print(query)
    find = hanap(query, neko)
    #print(find)
    obj = dict()
    i = 0
    for data in find:
        data1 = str(data)
        data1 = data1.replace("[", "")
        data1 = data1.replace("]", "")
        data1 = data1.replace("(", "")
        data1 = data1.replace(")", "")
        data1 = data1.replace("'", "")
        data1 = data1.split(",")
        obj["link" + str(i)] = data1[0]
        obj["score" + str(i)] = data1[1]
        obj["tags" + str(i)] = data1[2]
        i += 1
    return obj


def hanap(query, neko):
    results = set()
    # to search
    for j in search(query, tld="co.in", num=6, stop=6, pause=1):
        try:
            response = requests.get(j)
            print(response.status_code)
            html = (response.content)
            soup = BeautifulSoup(html, features="html.parser")
            #name = j.replace(":", "@")
            #name = name.replace("/", "AAAA")
            # kill all script and style elements
            for script in soup(["script", "style"]):
                script.extract()  # rip it out

            # get text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            # break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines
                      for phrase in line.split("  "))
            # drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)
            q = re.sub('[^A-Za-z0-9]+', ' ', neko.lower())
            t = re.sub('[^A-Za-z0-9]+', ' ', text.lower())

            #cosine = get_cosine(vector1, vector2)
            #cosine = compute_similarity_and_diff(t.lower(), q.lower())

            list1 = q.split(" ")
            list2 = t.split(" ")

            names1 = [name1 for name1 in list1 if name1 not in list2]
            cosine = sim(list1, list2)
            common = " ".join(names1)
            common = common.replace(",", " ")
            #print(common)
            try:
                #common = re.sub('[^A-Za-z0-9\ ]', ' ', common)
                score = j, cosine, common
                #print(score)
                #print(results)
                results.add(score)
            except:
                mahika = ""

        except:
            print("404")
    return results


def lcs(S, T):
    m = len(S)
    n = len(T)
    counter = [[0] * (n + 1) for x in range(m + 1)]
    longest = 0
    lcs_set = set()
    for i in range(m):
        for j in range(n):
            if S[i] == T[j]:
                c = counter[i][j] + 1
                counter[i + 1][j + 1] = c
                if c > longest:
                    lcs_set = set()
                    longest = c
                    lcs_set.add(S[i - c + 1:i + 1])
                elif c == longest:
                    lcs_set.add(S[i - c + 1:i + 1])
    return lcs_set


def compute_similarity_and_diff(text1, text2):
    from difflib import SequenceMatcher
    s = SequenceMatcher(None, text2, text1)
    return s.ratio()


def sim(a, b):
    # count word occurrences
    a_vals = Counter(a)
    b_vals = Counter(b)

    # convert to word-vectors
    words = list(a_vals.keys() | b_vals.keys())
    a_vect = [a_vals.get(word, 0) for word in words]  # [0, 0, 1, 1, 2, 1]
    b_vect = [b_vals.get(word, 0) for word in words]  # [1, 1, 1, 0, 1, 0]

    len_a = sum(av * av for av in a_vect)**0.5  # sqrt(7)
    len_b = sum(bv * bv for bv in b_vect)**0.5  # sqrt(4)
    dot = sum(av * bv for av, bv in zip(a_vect, b_vect))  # 3
    cosine = dot / (len_a * len_b)
    return cosine


app.run(host='0.0.0.0', port=80)
