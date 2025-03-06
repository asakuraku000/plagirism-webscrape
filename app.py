import math
import re
import requests
import concurrent.futures
from collections import Counter
from bs4 import BeautifulSoup
from googlesearch import search
from flask import Flask, request, render_template_string

app = Flask(__name__)

def hanap(query, neko):
    """
    Search and analyze web pages based on the input query with parallel processing.

    Args:
        query (str): The search query
        neko (str): Original query for comparison

    Returns:
        list: A sorted list of tuples containing (link, similarity score, unique words)
    """
    results = set()
    
    try:
        # Get search URLs first
        search_urls = list(search(query, tld="co.in", num=5, stop=5, pause=0.2))
        
        # Process URLs in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Map the process_url function to all URLs
            future_to_url = {executor.submit(process_url, url, neko): url for url in search_urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.add(result)
                except Exception as e:
                    print(f"Error processing {url}: {e}")
                    
    except Exception as e:
        print(f"Search error: {e}")
    
    # Sort and filter results
    sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
    filtered_results = [result for result in sorted_results if result[1] >= 0.6][:4]
    
    return filtered_results

def process_url(url, neko):
    """
    Process a single URL and return results.
    
    Args:
        url (str): The URL to process
        neko (str): Original query for comparison
        
    Returns:
        tuple: (url, similarity score, unique words) or None if error
    """
    try:
        # Add timeout to prevent hanging on slow websites
        response = requests.get(url, timeout=3)
        html = response.content
        
        # Use lxml parser for better performance
        try:
            soup = BeautifulSoup(html, features="lxml")
        except:
            # Fallback to html.parser if lxml is not installed
            soup = BeautifulSoup(html, features="html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Extract text from the webpage
        text = soup.get_text()
        
        # Limit text processing to first 5000 characters for speed
        if len(text) > 5000:
            text = text[:5000]
            
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Normalize query and text
        q = re.sub('[^A-Za-z0-9]+', ' ', neko.lower())
        t = re.sub('[^A-Za-z0-9]+', ' ', text.lower())
        
        # Calculate similarity with optimized method
        list1 = q.split()
        list2 = t.split()
        
        names1 = [name1 for name1 in list1 if name1 not in list2]
        cosine = sim(list1, list2)
        common = " ".join(names1)
        common = common.replace(",", " ")
        
        return (url, cosine, common)
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def sim(a, b):
    """
    Calculate cosine similarity between two lists of words.
    Optimized version for faster computation.

    Args:
        a (list): First list of words
        b (list): Second list of words

    Returns:
        float: Cosine similarity score
    """
    # If either list is empty, return 0
    if not a or not b:
        return 0
        
    # Count word occurrences
    a_vals = Counter(a)
    b_vals = Counter(b)
    
    # Optimization: Only use words that appear in both sets for dot product
    dot = sum(a_vals[word] * b_vals[word] for word in a_vals if word in b_vals)
    
    # Calculate magnitudes
    len_a = sum(count * count for count in a_vals.values())**0.5
    len_b = sum(count * count for count in b_vals.values())**0.5
    
    # Prevent division by zero
    if len_a * len_b == 0:
        return 0
        
    return dot / (len_a * len_b)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    query = ""
    
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        
        if query:
            results = hanap(query, query)
    
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Web Search Similarity Analyzer</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
                background-color: #f5f5f5;
            }
            h1 {
                color: #333;
                border-bottom: 2px solid #ddd;
                padding-bottom: 10px;
            }
            .container {
                background-color: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            form {
                margin-bottom: 20px;
            }
            textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                height: 100px;
                font-family: inherit;
                resize: vertical;
                margin-bottom: 10px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
            .result {
                margin: 20px 0;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f9f9f9;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .score-high {
                color: green;
                font-weight: bold;
            }
            .score-medium {
                color: orange;
                font-weight: bold;
            }
            .score-low {
                color: red;
            }
            a {
                color: #0066cc;
                text-decoration: none;
                word-break: break-all;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Web Search Similarity Analyzer</h1>
            <form action="/" method="post">
                <label for="query">Enter your search query:</label>
                <textarea id="query" name="query" required>{{ query }}</textarea>
                <button type="submit" id="search-button">Search</button>
            </form>
            
            <div id="loading" class="loading">
                <p>Searching and analyzing results, please wait...</p>
            </div>
            
            <div id="results">
                {% if results %}
                    <h2>Top Search Results (60%+ Similarity)</h2>
                    {% for link, score, tags in results %}
                        <div class="result">
                            <h3>Result {{ loop.index }}</h3>
                            <p><strong>Link:</strong> <a href="{{ link }}" target="_blank">{{ link }}</a></p>
                            {% if score >= 0.8 %}
                                <p><strong>Similarity Score:</strong> <span class="score-high">{{ "%.4f"|format(score) }}</span></p>
                            {% elif score >= 0.7 %}
                                <p><strong>Similarity Score:</strong> <span class="score-medium">{{ "%.4f"|format(score) }}</span></p>
                            {% else %}
                                <p><strong>Similarity Score:</strong> <span class="score-low">{{ "%.4f"|format(score) }}</span></p>
                            {% endif %}
                            <p><strong>Unique Words:</strong> {{ tags }}</p>
                        </div>
                    {% endfor %}
                {% elif request.method == 'POST' %}
                    <p>No results found meeting the 60% similarity threshold.</p>
                {% endif %}
            </div>
        </div>
        
        <script>
            document.querySelector('form').addEventListener('submit', function() {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';
                document.getElementById('search-button').disabled = true;
            });
        </script>
    </body>
    </html>
    '''
    
    return render_template_string(html_template, query=query, results=results)

if __name__ == "__main__":
    app.run(debug=True)
