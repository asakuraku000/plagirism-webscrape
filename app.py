import requests
from bs4 import BeautifulSoup
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import textwrap
import time
import json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def google_search(query, api_key, cx, num=3):
    """
    Perform a Google search and return the top results.
    
    Args:
        query (str): Search query
        api_key (str): Google API key
        cx (str): Google Custom Search Engine ID
        num (int): Number of results to return
    
    Returns:
        list: List of dictionaries containing title, link, and snippet
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": num
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        results = response.json()
        
        if "items" in results:
            return [{"title": item["title"], 
                     "link": item["link"], 
                     "snippet": item["snippet"]} 
                    for item in results["items"]]
        else:
            return []
    
    except requests.exceptions.RequestException as e:
        return []

def scrape_content(url):
    """
    Scrape the main content from a webpage.
    
    Args:
        url (str): URL to scrape
    
    Returns:
        str: Extracted content
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text(separator=' ')
        
        # Clean text (remove extra whitespace)
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    except Exception as e:
        return ""

def calculate_similarity(text1, text2):
    """
    Calculate cosine similarity between two texts.
    
    Args:
        text1 (str): First text
        text2 (str): Second text
    
    Returns:
        float: Cosine similarity score (0-1)
    """
    if not text1 or not text2:
        return 0.0
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer()
    
    try:
        # Create TF-IDF matrix
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    
    except Exception as e:
        return 0.0

def split_long_query(query, words_per_chunk=500):
    """
    Split a long query into chunks of approximately 500 words.
    
    Args:
        query (str): Long query text
        words_per_chunk (int): Maximum number of words per chunk
    
    Returns:
        list: List of query chunks
    """
    words = query.split()
    
    # If query is shorter than the limit, return it as is
    if len(words) <= words_per_chunk:
        return [query]
    
    # Split into chunks of approximately 500 words
    chunks = []
    for i in range(0, len(words), words_per_chunk):
        chunk = ' '.join(words[i:i + words_per_chunk])
        chunks.append(chunk)
    
    return chunks

def get_plagiarism_level(similarity):
    """
    Determine plagiarism level based on similarity score.
    
    Args:
        similarity (float): Similarity score (0-1)
    
    Returns:
        tuple: (level, description, color_code)
    """
    if similarity >= 0.80:
        return ("CRITICAL", "Highly likely plagiarism", "red")
    elif similarity >= 0.60:
        return ("HIGH", "Substantial similarity detected", "orange")
    elif similarity >= 0.40:
        return ("MODERATE", "Moderate similarity detected", "yellow")
    elif similarity >= 0.20:
        return ("LOW", "Minor similarity detected", "green")
    else:
        return ("NEGLIGIBLE", "Likely original content", "blue")

def check_plagiarism(essay_text, api_key, cx):
    """
    Check an essay for plagiarism.
    
    Args:
        essay_text (str): The essay text to check
        api_key (str): Google API key
        cx (str): Google Custom Search Engine ID
    
    Returns:
        dict: Plagiarism check results
    """
    # Split the query if it's long (approximately 500 words per chunk)
    query_parts = split_long_query(essay_text)
    
    # Track all unique search results
    all_results = []
    unique_links = set()
    
    # Process each query part
    for i, part in enumerate(query_parts):
        # Search for this query part
        search_results = google_search(part, api_key, cx, num=3)
        
        if not search_results:
            continue
        
        # Add only unique links
        for result in search_results:
            if result["link"] not in unique_links:
                unique_links.add(result["link"])
                all_results.append(result)
        
        # Add a small delay to avoid hitting API rate limits
        if i < len(query_parts) - 1:
            time.sleep(1)
    
    # Process each unique result
    plagiarism_results = []
    
    for result in all_results:
        # Scrape the content
        content = scrape_content(result['link'])
        if not content:
            continue
        
        # Calculate similarity against each part
        part_similarities = []
        for part in query_parts:
            similarity = calculate_similarity(part, content)
            part_similarities.append(similarity)
        
        # Calculate average similarity
        avg_similarity = sum(part_similarities) / len(part_similarities)
        
        # Calculate maximum similarity (most similar part)
        max_similarity = max(part_similarities)
        max_similar_part = part_similarities.index(max_similarity) + 1
        
        # Get plagiarism assessment
        plagiarism_level, description, color = get_plagiarism_level(max_similarity)
        
        # Store the result
        plagiarism_results.append({
            "title": result['title'],
            "link": result['link'],
            "part_similarities": [float(sim) for sim in part_similarities],  # Ensure JSON serializable
            "max_similarity": float(max_similarity),  # Ensure JSON serializable
            "max_similar_part": max_similar_part,
            "avg_similarity": float(avg_similarity),  # Ensure JSON serializable
            "plagiarism_level": plagiarism_level,
            "description": description,
            "color": color
        })
    
    # Sort by maximum similarity (highest first)
    plagiarism_results.sort(key=lambda x: x['max_similarity'], reverse=True)
    
    if not plagiarism_results:
        return {
            "success": False,
            "message": "No sources were successfully analyzed. Try again with different text."
        }
    
    # Calculate overall plagiarism score (weighted average of top 3)
    weights = [0.6, 0.3, 0.1]  # 60% weight to highest, 30% to second, 10% to third
    top_results = plagiarism_results[:min(3, len(plagiarism_results))]
    
    if len(top_results) == 1:
        overall_score = top_results[0]['max_similarity']
    elif len(top_results) == 2:
        normalized_weights = [0.7, 0.3]  # Adjust if only 2 results
        overall_score = sum(r['max_similarity'] * w for r, w in zip(top_results, normalized_weights))
    else:
        overall_score = sum(r['max_similarity'] * w for r, w in zip(top_results, weights))
    
    overall_level, overall_desc, overall_color = get_plagiarism_level(overall_score)
    
    return {
        "success": True,
        "essay_parts": len(query_parts),
        "sources_analyzed": len(plagiarism_results),
        "overall_score": float(overall_score),
        "overall_percentage": round(float(overall_score) * 100, 1),
        "assessment": overall_level,
        "description": overall_desc,
        "color": overall_color,
        "top_sources": plagiarism_results
    }

@app.route('/')
def index():
    """Render the home page with the submission form."""
    return render_template('index.html')

@app.route('/api/check-plagiarism', methods=['POST'])
def api_check_plagiarism():
    """API endpoint to check essay for plagiarism."""
    # Get data from request
    data = request.json
    
    if not data or 'essay' not in data:
        return jsonify({
            "success": False,
            "message": "Essay text is required."
        }), 400
    
    # Get essay text
    essay_text = data['essay']
    
    # API credentials
    api_key = "AIzaSyDnMPyjZv76NaXXXJhsykc6BU7FP-gvdX8"  # Replace with your actual API key
    cx = "4233ed3f6435f4486"  # Replace with your actual search engine ID
    
    # Check for plagiarism
    results = check_plagiarism(essay_text, api_key, cx)
    
    return jsonify(results)

@app.route('/check', methods=['POST'])
def check_essay():
    """Web form submission handler to check essay for plagiarism."""
    # Get essay text from form
    essay_text = request.form.get('essay', '')
    
    if not essay_text:
        return render_template('index.html', error="Essay text is required.")
    
    # API credentials
    api_key = "AIzaSyDnMPyjZv76NaXXXJhsykc6BU7FP-gvdX8"  # Replace with your actual API key
    cx = "4233ed3f6435f4486"  # Replace with your actual search engine ID
    
    # Check for plagiarism
    results = check_plagiarism(essay_text, api_key, cx)
    
    if not results['success']:
        return render_template('index.html', error=results['message'], essay=essay_text)
    
    return render_template('results.html', results=results, essay=essay_text)

# Create templates directory and HTML templates
@app.route('/templates/<path:path>')
def serve_template(path):
    with open(f'templates/{path}', 'r') as f:
        return f.read()

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    import os
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create index.html template
    with open('templates/index.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plagiarism Checker</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        textarea {
            width: 100%;
            height: 300px;
            padding: 10px;
            font-family: inherit;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 20px;
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
        .error {
            color: red;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>Plagiarism Checker</h1>
    <p>Paste your essay below to check for plagiarism.</p>
    
    {% if error %}
    <div class="error">{{ error }}</div>
    {% endif %}
    
    <form action="/check" method="post">
        <textarea name="essay" placeholder="Enter your essay text here...">{{ essay if essay else '' }}</textarea>
        <button type="submit">Check for Plagiarism</button>
    </form>
    
    <p>You can also use our API by sending a POST request to <code>/api/check-plagiarism</code> with a JSON payload containing your essay text.</p>
    <pre>
{
  "essay": "Your essay text here"
}
    </pre>
</body>
</html>''')
    
    # Create results.html template
    with open('templates/results.html', 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plagiarism Check Results</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2 {
            color: #333;
        }
        .result-summary {
            margin: 20px 0;
            padding: 15px;
            border-radius: 4px;
        }
        .CRITICAL {
            background-color: #ffebee;
            border-left: 5px solid #f44336;
        }
        .HIGH {
            background-color: #fff3e0;
            border-left: 5px solid #ff9800;
        }
        .MODERATE {
            background-color: #fffde7;
            border-left: 5px solid #ffeb3b;
        }
        .LOW {
            background-color: #e8f5e9;
            border-left: 5px solid #4caf50;
        }
        .NEGLIGIBLE {
            background-color: #e3f2fd;
            border-left: 5px solid #2196f3;
        }
        .source {
            margin-bottom: 30px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .similarity-bar {
            height: 20px;
            background-color: #eee;
            margin: 10px 0;
            border-radius: 10px;
            overflow: hidden;
        }
        .similarity-fill {
            height: 100%;
            border-radius: 10px;
        }
        .red { background-color: #f44336; }
        .orange { background-color: #ff9800; }
        .yellow { background-color: #ffeb3b; }
        .green { background-color: #4caf50; }
        .blue { background-color: #2196f3; }
        .back-button {
            display: inline-block;
            background-color: #2196f3;
            color: white;
            padding: 10px 15px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>Plagiarism Check Results</h1>
    
    <div class="result-summary {{ results.assessment }}">
        <h2>Overall Assessment: {{ results.assessment }}</h2>
        <p>{{ results.description }}</p>
        <p>Overall similarity score: {{ results.overall_percentage }}%</p>
        <div class="similarity-bar">
            <div class="similarity-fill {{ results.color }}" style="width: {{ results.overall_percentage }}%;"></div>
        </div>
        <p>Essay was split into {{ results.essay_parts }} parts. {{ results.sources_analyzed }} sources were analyzed.</p>
    </div>
    
    <h2>Top Matching Sources</h2>
    
    {% if results.top_sources %}
        {% for source in results.top_sources %}
            <div class="source">
                <h3>{{ loop.index }}. {{ source.title }}</h3>
                <p><strong>URL:</strong> <a href="{{ source.link }}" target="_blank">{{ source.link }}</a></p>
                <p><strong>Similarity:</strong> {{ (source.max_similarity * 100) | round(1) }}% (in part {{ source.max_similar_part }})</p>
                <div class="similarity-bar">
                    <div class="similarity-fill {{ source.color }}" style="width: {{ (source.max_similarity * 100) | round(1) }}%;"></div>
                </div>
                <p><strong>Assessment:</strong> {{ source.plagiarism_level }} - {{ source.description }}</p>
                
                {% if source.part_similarities and source.part_similarities|length > 1 %}
                    <h4>Part-by-part similarity:</h4>
                    <ul>
                        {% for sim in source.part_similarities %}
                            <li>Part {{ loop.index }}: {{ (sim * 100) | round(1) }}%</li>
                        {% endfor %}
                    </ul>
                {% endif %}
            </div>
        {% endfor %}
    {% else %}
        <p>No matching sources found.</p>
    {% endif %}
    
    <a href="/" class="back-button">Check Another Essay</a>
</body>
</html>''')
    
    # Run the Flask app
    app.run(debug=True)
