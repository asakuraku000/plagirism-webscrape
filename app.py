import math
import re
import requests
from collections import Counter
import nltk
from nltk.tokenize import sent_tokenize
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
try:
    from googlesearch import search
except ImportError:
    print("Warning: googlesearch module not found. Using fallback.")
    # Define a simple fallback function
    def search(query, **kwargs):
        return ["https://example.com/fallback"]
from flask import Flask, request, jsonify

# Download NLTK data for sentence tokenization
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handle both GET and POST requests with text to check for plagiarism.
    Returns JSON with similarity results.
    """
    # Get query from request parameters or POST data
    if request.method == 'POST':
        # Handle POST request
        if request.is_json:
            data = request.get_json()
            query = data.get('data', '')
        else:
            query = request.form.get('data', '')
    else:
        # Handle GET request
        query = request.args.get('data', default='', type=str)
    
    if not query or query == '*':
        return jsonify({"error": "No text provided. Please add ?data=your text to check or POST data"})
    
    neko = query  # Keep original text
    
    # Perform the search and analysis
    find = hanap(query, neko)
    
    # Format results as JSON object
    obj = dict()
    i = 0
    for data in find:
        # Extract data from tuple
        link, score, word_tags, longest_match, match_ratio = data
        
        # Add to response object
        obj["link" + str(i)] = link
        obj["score" + str(i)] = str(score)
        obj["word_tags" + str(i)] = word_tags
        obj["longest_match" + str(i)] = longest_match
        obj["match_ratio" + str(i)] = str(match_ratio)
        i += 1
    
    # Return empty object if no results found
    if not obj:
        obj["message"] = "No similar content found above threshold"
    
    return jsonify(obj)

@app.route('/ping')
def ping():
    """Simple health check endpoint"""
    return "pong"

def clean_text(text):
    """Clean and normalize text for comparison"""
    # Remove special characters and convert to lowercase
    return re.sub('[^A-Za-z0-9]+', ' ', text.lower()).strip()

def find_longest_matching_substring(text1, text2):
    """Find the longest matching substring between two texts"""
    matcher = SequenceMatcher(None, text1, text2)
    match = matcher.find_longest_match(0, len(text1), 0, len(text2))
    
    if match.size > 5:  # Only consider matches with more than 5 characters
        return text1[match.a:match.a + match.size], match.size / len(text1) if len(text1) > 0 else 0
    return "", 0

def find_matching_sentences(original_text, web_text, threshold=0.8):
    """Find matching sentences between original text and web content"""
    # Tokenize both texts into sentences
    original_sentences = sent_tokenize(original_text)
    web_sentences = sent_tokenize(web_text)
    
    matches = []
    
    # Compare each sentence from original text with each sentence from web text
    for orig_sent in original_sentences:
        orig_clean = clean_text(orig_sent)
        if len(orig_clean) < 20:  # Skip very short sentences
            continue
            
        for web_sent in web_sentences:
            web_clean = clean_text(web_sent)
            
            # Calculate similarity ratio between sentences
            similarity = SequenceMatcher(None, orig_clean, web_clean).ratio()
            
            if similarity >= threshold:
                matches.append((orig_sent, web_sent, similarity))
    
    # Sort matches by similarity in descending order
    matches.sort(key=lambda x: x[2], reverse=True)
    
    if matches:
        # Return the most similar match
        return matches[0][0], matches[0][2]
    else:
        # Find the longest matching substring as a fallback
        substring, ratio = find_longest_matching_substring(clean_text(original_text), clean_text(web_text))
        return substring, ratio

def hanap(query, neko):
    """
    Search and analyze web pages based on the input query.

    Args:
        query (str): The search query
        neko (str): Original query for comparison

    Returns:
        list: A sorted list of tuples containing (link, similarity score, unique words, longest match, match ratio)
    """
    results = set()

    try:
        # Use more strategic search queries
        search_queries = [
            query,  # Original query
            ' '.join(query.split()[:10]),  # First 10 words
            ' '.join(query.split()[-10:])  # Last 10 words
        ]
        
        processed_urls = set()
        
        for search_query in search_queries:
            # Search for web pages
            for j in search(search_query, tld="co.in", num=8, stop=8, pause=1):
                if j in processed_urls:
                    continue
                
                processed_urls.add(j)
                
                try:
                    response = requests.get(j, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    print(f"Checking {j} - Status: {response.status_code}")
                    
                    if response.status_code != 200:
                        continue
                    
                    html = response.content
                    soup = BeautifulSoup(html, features="html.parser")

                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.extract()

                    # Extract text from the webpage
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)

                    # Normalize query and text
                    q = clean_text(neko)
                    t = clean_text(text)

                    # Calculate word-based similarity
                    list1 = q.split()
                    list2 = t.split()

                    unique_words = [word for word in list1 if word not in list2]
                    cosine = sim(list1, list2)
                    unique_words_str = " ".join(unique_words)
                    
                    # Find longest matching sentences
                    longest_match, match_ratio = find_matching_sentences(neko, text)

                    # Add result to set if either cosine similarity or sentence match is high enough
                    if cosine >= 0.5 or match_ratio >= 0.7:
                        score = (j, cosine, unique_words_str, longest_match, match_ratio)
                        results.add(score)

                except Exception as e:
                    print(f"Error processing {j}: {e}")

    except Exception as e:
        print(f"Search error: {e}")

    # Convert set to list for sorting
    results_list = list(results)
    
    # Calculate combined score that considers both word similarity and sentence matching
    def combined_score(result):
        word_sim = result[1]  # Cosine similarity
        sent_match = result[4]  # Sentence match ratio
        return 0.4 * word_sim + 0.6 * sent_match  # Weighted average
    
    # Sort results by combined score
    sorted_results = sorted(results_list, key=combined_score, reverse=True)
    
    # Return top 5 results
    return sorted_results[:5]

def sim(a, b):
    """
    Calculate cosine similarity between two lists of words.

    Args:
        a (list): First list of words
        b (list): Second list of words

    Returns:
        float: Cosine similarity score
    """
    # Count word occurrences
    a_vals = Counter(a)
    b_vals = Counter(b)

    # Convert to word-vectors
    words = list(a_vals.keys() | b_vals.keys())
    a_vect = [a_vals.get(word, 0) for word in words]
    b_vect = [b_vals.get(word, 0) for word in words]

    len_a = sum(av * av for av in a_vect)**0.5
    len_b = sum(bv * bv for bv in b_vect)**0.5
    dot = sum(av * bv for av, bv in zip(a_vect, b_vect))

    # Prevent division by zero
    cosine = dot / (len_a * len_b) if len_a * len_b != 0 else 0
    return cosine

# If running locally or on Render, this will start the server
if __name__ == '__main__':
    import os
    app.run(debug=True)

# For PythonAnywhere and other WSGI compatibility
application = app
