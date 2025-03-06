import math
import re
import requests
from collections import Counter
from bs4 import BeautifulSoup
from googlesearch import search
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    """
    Handle GET requests with a 'data' parameter containing the text to check for plagiarism.
    Returns JSON with similarity results.
    """
    # Get query from request parameters
    query = request.args.get('data', default='', type=str)
    
    if not query or query == '*':
        return jsonify({"error": "No text provided. Please add ?data=your text to check"})
    
    neko = query  # Keep original text
    
    # Optional: For very long texts, you can use a shorter version for search
    # Commented out but kept from your original code
    '''
    if (len(query) >= 100):
        query = query.split(" ")
        key = ""
        for i in range(0, 40):
            key += query[i] + " "
        query = key
    '''
    
    # Perform the search and analysis
    find = hanap(query, neko)
    
    # Format results as JSON object
    obj = dict()
    i = 0
    for data in find:
        # Extract data from tuple
        link, score, tags = data
        
        # Add to response object
        obj["link" + str(i)] = link
        obj["score" + str(i)] = str(score)
        obj["tags" + str(i)] = tags
        i += 1
    
    # Return empty object if no results found
    if not obj:
        obj["message"] = "No similar content found above threshold"
    
    return jsonify(obj)

def hanap(query, neko):
    """
    Search and analyze web pages based on the input query.

    Args:
        query (str): The search query
        neko (str): Original query for comparison

    Returns:
        list: A sorted list of tuples containing (link, similarity score, unique words)
    """
    results = set()

    try:
        # Search for web pages
        for j in search(query, tld="co.in", num=6, stop=6, pause=1):
            try:
                response = requests.get(j)
                print(f"Checking {j} - Status: {response.status_code}")
                
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
                q = re.sub('[^A-Za-z0-9]+', ' ', neko.lower())
                t = re.sub('[^A-Za-z0-9]+', ' ', text.lower())

                # Calculate similarity
                list1 = q.split()
                list2 = t.split()

                names1 = [name1 for name1 in list1 if name1 not in list2]
                cosine = sim(list1, list2)
                common = " ".join(names1)
                common = common.replace(",", " ")

                # Add result to set
                try:
                    score = (j, cosine, common)
                    results.add(score)
                except Exception as e:
                    print(f"Error adding result: {e}")

            except Exception as e:
                print(f"Error processing {j}: {e}")

    except Exception as e:
        print(f"Search error: {e}")

    # Sort results by similarity score in descending order
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)

    # Filter results to keep only those above 60% similarity and top 4
    filtered_results = [result for result in sorted_results if result[1] >= 0.6][:4]

    return filtered_results

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

# If running locally (not on PythonAnywhere), this will start the server
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# For PythonAnywhere compatibility
application = app