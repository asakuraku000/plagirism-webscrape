from flask import Flask, request, jsonify
import re
import requests
import nltk
from nltk.tokenize import sent_tokenize
from collections import Counter
from googlesearch import search
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

# Download NLTK data for sentence tokenization
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

@app.route('/', methods=['GET'])
def index():
    os.system('cls' if os.name == 'nt' else 'clear')
    query = request.args.get('data', default='*', type=str)
    print(f"GET request with query: {query}")
    
    results = search_by_sentence_chunks(query)
    
    return jsonify(results)

@app.route('/', methods=['POST'])
def process_post():
    # Get JSON data from request body
    if request.is_json:
        data = request.get_json()
        query = data.get('data', '*')
    else:
        # Handle form data
        query = request.form.get('data', '*')
    
    print(f"POST request with query: {query}")
    
    results = search_by_sentence_chunks(query)
    
    return jsonify(results)

def search_by_sentence_chunks(text):
    # Split the text into sentences
    sentences = sent_tokenize(text)
    
    # Group sentences into chunks of 5
    sentence_chunks = [sentences[i:i+5] for i in range(0, len(sentences), 5)]
    
    results = {}
    
    for i, chunk in enumerate(sentence_chunks):
        chunk_text = " ".join(chunk)
        print(f"Searching for chunk {i+1}: {chunk_text[:50]}...")
        
        # Search for each chunk
        chunk_results = search_web(chunk_text)
        
        if chunk_results:
            # Take only the top result for each chunk
            top_result = chunk_results[0]
            
            results[f"chunk_{i+1}"] = {
                "sentences": chunk,
                "search_result": {
                    "link": top_result["link"],
                    "similarity_score": top_result["similarity_score"],
                    "missing_terms": top_result["missing_terms"]
                }
            }
        else:
            results[f"chunk_{i+1}"] = {
                "sentences": chunk,
                "search_result": {
                    "link": "No results found",
                    "similarity_score": 0,
                    "missing_terms": ""
                }
            }
    
    return results

def search_web(query):
    results = []
    
    # Perform Google search
    try:
        for j in search(query, tld="co.in", num=3, stop=3, pause=1):
            try:
                response = requests.get(j, timeout=5)
                print(f"URL: {j}, Status code: {response.status_code}")
                
                if response.status_code == 200:
                    html = response.content
                    soup = BeautifulSoup(html, features="html.parser")
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.extract()
                    
                    # Extract text
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    # Clean and calculate similarity
                    clean_query = re.sub('[^A-Za-z0-9]+', ' ', query.lower())
                    clean_text = re.sub('[^A-Za-z0-9]+', ' ', text.lower())
                    
                    query_words = clean_query.split()
                    page_words = clean_text.split()
                    
                    # Find missing terms
                    missing_terms = [word for word in query_words if word not in page_words]
                    
                    # Calculate cosine similarity
                    similarity_score = calculate_cosine_similarity(query_words, page_words)
                    
                    results.append({
                        "link": j,
                        "similarity_score": round(similarity_score, 3),
                        "missing_terms": " ".join(missing_terms)
                    })
            except Exception as e:
                print(f"Error processing URL {j}: {str(e)}")
    except Exception as e:
        print(f"Search error: {str(e)}")
    
    # Sort results by similarity score
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return results

def calculate_cosine_similarity(a, b):
    # Count word occurrences
    a_vals = Counter(a)
    b_vals = Counter(b)
    
    # Get unique words from both lists
    words = list(a_vals.keys() | b_vals.keys())
    
    # Convert to word-vectors
    a_vect = [a_vals.get(word, 0) for word in words]
    b_vect = [b_vals.get(word, 0) for word in words]
    
    # Calculate dot product and magnitudes
    dot = sum(av * bv for av, bv in zip(a_vect, b_vect))
    len_a = sum(av * av for av in a_vect) ** 0.5
    len_b = sum(bv * bv for bv in b_vect) ** 0.5
    
    # Avoid division by zero
    if len_a == 0 or len_b == 0:
        return 0
    
    # Calculate cosine similarity
    cosine = dot / (len_a * len_b)
    return cosine

if __name__ == '__main__':
    app.run(port=5000)
