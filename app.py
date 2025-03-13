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

@app.route('/analyze', methods=['POST'])
def analyze_essay():
    """
    API endpoint to analyze an essay for web similarity.
    
    Expects JSON input with 'essay' field.
    Returns JSON with analysis results.
    """
    # Check if request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    # Get the essay from the request
    data = request.get_json()
    
    if 'essay' not in data:
        return jsonify({"error": "Missing 'essay' field in request"}), 400
    
    essay = data['essay']
    
    # Validate essay
    if not essay or len(essay.strip()) < 10:
        return jsonify({"error": "Essay too short for meaningful analysis"}), 400
    
    # Perform search and analysis
    # Use a truncated version for the search query if essay is very long
    search_text = essay[:1000] if len(essay) > 1000 else essay
    results = hanap(search_text, essay)
    
    # Format results for JSON response
    formatted_results = []
    for link, score, unique_words in results:
        formatted_results.append({
            "link": link,
            "similarity_score": round(score, 4),
            "unique_words": unique_words
        })
    
    # Calculate overall metrics
    avg_similarity = sum(item["similarity_score"] for item in formatted_results) / len(formatted_results) if formatted_results else 0
    
    response = {
        "analysis_timestamp": request.date,
        "overall_similarity": round(avg_similarity, 4),
        "analyzed_length": len(essay),
        "search_results": formatted_results,
        "total_matches": len(formatted_results)
    }
    
    return jsonify(response)

@app.route('/', methods=['GET'])
def home():
    """Simple home page with usage instructions."""
    return """
    <html>
        <head>
            <title>Essay Similarity Analysis API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
                pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>Essay Similarity Analysis API</h1>
            <p>This API analyzes essays for web similarity.</p>
            
            <h2>Usage:</h2>
            <p>Send a POST request to <code>/analyze</code> with JSON data containing your essay:</p>
            
            <pre>
curl -X POST http://localhost:5000/analyze \\
     -H "Content-Type: application/json" \\
     -d '{"essay": "Your essay text goes here..."}'
            </pre>
            
            <h2>Response:</h2>
            <p>The API will return a JSON response with similarity analysis results.</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)
    
