from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for flash messages and session

# In-memory storage for essays (in a real app, you'd use a database)
essays = []

@app.route('/')
def index():
    """Render the home page with the essay submission form"""
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_essay():
    """Handle essay submission"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        content = request.form.get('content', '').strip()
        
        # Basic validation
        if not title or not content:
            flash('Both title and content are required!', 'error')
            return redirect(url_for('index'))
        
        # Create essay entry
        essay = {
            'id': str(uuid.uuid4()),
            'title': title,
            'author': author if author else 'Anonymous',
            'content': content,
            'submitted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save essay
        essays.append(essay)
        
        flash('Essay submitted successfully!', 'success')
        return redirect(url_for('view_essays'))
    
@app.route('/essays')
def view_essays():
    """Display all submitted essays"""
    return render_template('essays.html', essays=essays)

@app.route('/essay/<essay_id>')
def view_essay(essay_id):
    """View a specific essay"""
    essay = next((e for e in essays if e['id'] == essay_id), None)
    if essay:
        return render_template('essay.html', essay=essay)
    flash('Essay not found!', 'error')
    return redirect(url_for('view_essays'))

# Define HTML templates as strings for a single-file solution
@app.route('/templates/<template_name>')
def get_template(template_name):
    return "Template not found", 404

# Register template rendering function
@app.template_global()
def render_template_string(template_name):
    templates = {
        'index.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Essay Submission</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; }
        input[type="text"], textarea { width: 100%; padding: 8px; }
        textarea { height: 300px; }
        button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #dff0d8; color: #3c763d; }
        .error { background-color: #f2dede; color: #a94442; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 10px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/essays">View Essays</a>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <h1>Submit Your Essay</h1>
    <form action="/submit" method="post">
        <div class="form-group">
            <label for="title">Title*</label>
            <input type="text" id="title" name="title" required>
        </div>
        
        <div class="form-group">
            <label for="author">Author (optional)</label>
            <input type="text" id="author" name="author">
        </div>
        
        <div class="form-group">
            <label for="content">Essay Content*</label>
            <textarea id="content" name="content" required></textarea>
        </div>
        
        <button type="submit">Submit Essay</button>
    </form>
</body>
</html>
        ''',
        'essays.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Submitted Essays</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .essay-list { margin-top: 20px; }
        .essay-item { border-bottom: 1px solid #eee; padding: 10px 0; }
        .essay-title { font-weight: bold; font-size: 18px; }
        .essay-meta { color: #777; font-size: 14px; margin: 5px 0; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #dff0d8; color: #3c763d; }
        .error { background-color: #f2dede; color: #a94442; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 10px; }
        .no-essays { color: #777; font-style: italic; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/essays">View Essays</a>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <h1>Submitted Essays</h1>
    
    <div class="essay-list">
        {% if essays %}
            {% for essay in essays %}
                <div class="essay-item">
                    <div class="essay-title">
                        <a href="/essay/{{ essay.id }}">{{ essay.title }}</a>
                    </div>
                    <div class="essay-meta">
                        By {{ essay.author }} on {{ essay.submitted_at }}
                    </div>
                    <div class="essay-preview">
                        {{ essay.content[:150] }}{% if essay.content|length > 150 %}...{% endif %}
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="no-essays">No essays have been submitted yet.</div>
        {% endif %}
    </div>
</body>
</html>
        ''',
        'essay.html': '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ essay.title }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        .essay-meta { color: #777; font-size: 14px; margin: 10px 0 20px; }
        .essay-content { line-height: 1.6; white-space: pre-wrap; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background-color: #dff0d8; color: #3c763d; }
        .error { background-color: #f2dede; color: #a94442; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 10px; }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/essays">View Essays</a>
    </div>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <h1>{{ essay.title }}</h1>
    <div class="essay-meta">
        By {{ essay.author }} on {{ essay.submitted_at }}
    </div>
    
    <div class="essay-content">
        {{ essay.content }}
    </div>
</body>
</html>
        '''
    }
    
    return templates.get(template_name, '')

# Override render_template to use our template strings
def render_template(template_name, **context):
    template_content = render_template_string(template_name)
    from flask import render_template_string as flask_render_template_string
    return flask_render_template_string(template_content, **context)

# Override Flask's render_template function
app.jinja_env.globals['render_template'] = render_template

if __name__ == '__main__':
    app.run(debug=True)
