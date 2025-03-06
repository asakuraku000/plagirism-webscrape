from flask import Flask, request, jsonify
import math
import re
import requests
import concurrent.futures
from collections import Counter
from bs4 import BeautifulSoup
from googlesearch import search

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

@app.route('/api/search', methods=['GET', 'POST'])
def search_api():
    """
    API endpoint for search similarity analysis.
    Supports both GET and POST methods.
    """
    if request.method == 'POST':
        # Handle POST method - get data from form or JSON body
        if request.is_json:
            data = request.get_json()
            query = data.get('query', '')
        else:
            query = request.form.get('query', '')
    else:
        # Handle GET method - get data from URL parameters
        query = request.args.get('query', '')
    
    # Validate input
    if not query:
        return jsonify({
            'success': False,
            'error': 'Please provide a valid search query'
        }), 400
    
    # Perform search and analysis
    try:
        results = hanap(query, query)
        
        # Format results for JSON response
        formatted_results = []
        for link, score, tags in results:
            formatted_results.append({
                'link': link,
                'similarity_score': round(score, 4),
                'unique_words': tags
            })
        
        # Return JSON response
        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

@app.route('/api/essay', methods=['GET', 'POST'])
def essay_api():
    """
    API endpoint for essay submission and similarity analysis.
    Supports both GET and POST methods.
    """
    if request.method == 'POST':
        # Handle POST method - get data from form or JSON body
        if request.is_json:
            data = request.get_json()
            essay = data.get('essay', '')
        else:
            essay = request.form.get('essay', '')
    else:
        # Handle GET method - get data from URL parameters
        essay = request.args.get('essay', '')
    
    # Validate input
    if not essay:
        return jsonify({
            'success': False,
            'error': 'Please provide essay content'
        }), 400
    
    # Use the essay as both the search query and comparison text
    try:
        # For longer essays, use first 500 characters for search query
        search_query = essay[:500] if len(essay) > 500 else essay
        results = hanap(search_query, essay)
        
        # Format results for JSON response
        formatted_results = []
        for link, score, tags in results:
            formatted_results.append({
                'link': link,
                'similarity_score': round(score, 4),
                'unique_words': tags
            })
        
        # Return JSON response
        return jsonify({
            'success': True,
            'essay_length': len(essay),
            'results': formatted_results,
            'count': len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }), 500

# Add a simple homepage
@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Search Similarity API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; }
                h1 { color: #333; }
                h2 { color: #555; margin-top: 20px; }
                pre { background: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
                code { font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Search Similarity API</h1>
                <p>This API provides search similarity analysis for queries and essays.</p>
                
                <h2>Endpoints:</h2>
                <h3>1. Search Query Analysis</h3>
                <code>GET/POST /api/search?query=your+search+query</code>
                <p>Submit a search query to analyze similarity with web results.</p>
                
                <h3>2. Essay Similarity Analysis</h3>
                <code>GET/POST /api/essay</code>
                <p>Submit an essay to check for similarities with web content.</p>
                
                <h2>Example Usage:</h2>
                <pre>curl -X POST -H "Content-Type: application/json" -d '{"query":"artificial intelligence"}' http://localhost:5000/api/search</pre>
                
                <p>For more information, see the documentation.</p>
            </div>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
