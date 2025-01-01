from flask import Flask, render_template, request, jsonify, session, redirect, g, url_for
import csv
import sqlite3
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'sdfguvh6678u8978'

DATABASE = 'video_library.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = get_db()
    if db is not None:
        db.close()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        # last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        roll = request.form['roll']
        role = request.form['role']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            message = "Passwords do not match"
            return render_template('register.html', message=message)

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (name, username, email, roll, role, password) VALUES (?, ?, ?, ?, ?, ?)",
                           (name, username, email, roll, role, password))
            db.commit()
        except sqlite3.IntegrityError:
            message =  'Username already exists'
            return render_template('register.html', message=message)
        
        message =  'Account created successfully'
        
        return render_template('login.html', message=message)

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        if user:
            # Set session variables to indicate user is logged in
            session['logged_in'] = True
            session['username'] = username
 
            return redirect(url_for('home', username=username))
        else:
            message =  'Invalid username or password'
            return render_template('login.html', message=message)

    return render_template('login.html')

@app.route('/')
@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    username = session['username']  # Retrieve username from session 
    return render_template('home.html', username=username)

@app.route('/contactus', methods=['GET', 'POST'])
def message():
    # Load data from CSV
    data = load_csv_data()

    # Extract unique options for branch, subject, unit, and video
    branches = sorted(set(row['BRANCH'] for row in data))
    subjects = sorted(set(row['SUBJECT'] for row in data))
    units = sorted(set(row['UNIT'] for row in data))
    videos = sorted(set(row['TITLE'] for row in data))

    # Group subjects, units, and videos by the respective parent
    branch_to_subjects = {branch: sorted(set(row['SUBJECT'] for row in data if row['BRANCH'] == branch)) for branch in branches}
    subject_to_units = {subject: sorted(set(row['UNIT'] for row in data if row['SUBJECT'] == subject)) for subject in subjects}
    unit_to_videos = {unit: sorted(set(row['TITLE'] for row in data if row['UNIT'] == unit)) for unit in units}

    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    username = session['username']  # Retrieve username from session 
    timestamp = datetime.now()

    if request.method == 'POST':
        # Get selected values from the form
        selected_branch = request.form['branch']
        selected_subject = request.form['subject']
        selected_unit = request.form['unit']
        selected_video = request.form['video_name']
        message = request.form['message']

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO feedback (username, branch, subject, unit, video_name, message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, selected_branch, selected_subject, selected_unit, selected_video, message, timestamp))

        
        db.commit()

        message = "Your query has been submitted successfully"
        
        print(f"Branch: {selected_branch}, Subject: {selected_subject}, Unit: {selected_unit}, Video: {selected_video}, Message: {message}")

        return render_template('contactus.html', branches=branches, subjects=subjects, units=units, videos=videos, 
                           branch_to_subjects=branch_to_subjects, subject_to_units=subject_to_units, unit_to_videos=unit_to_videos, message=message)

    return render_template('contactus.html', branches=branches, subjects=subjects, units=units, videos=videos, 
                           branch_to_subjects=branch_to_subjects, subject_to_units=subject_to_units, unit_to_videos=unit_to_videos)


@app.route('/logout')
def logout():
    # Clear session variables
    session.clear()
    return redirect('/')


def load_csv_data():
    data = []
    try:
        with open('link_data.csv', 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Check if all required fields are not null or blank
                if all(row[key] not in (None, '', ' ') for key in row):
                    data.append(row)
    except UnicodeDecodeError:
        with open('link_data.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Check if all required fields are not null or blank
                if all(row[key] not in (None, '', ' ') for key in row):
                    data.append(row)
    return data

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    username = session['username']  # Retrieve username from session 
    data = load_csv_data()
    branches = sorted(set(item['BRANCH'] for item in data))

    return render_template('index.html', branches=branches, username=username)


@app.route('/get_subjects/<branch>')
def get_subjects(branch):
    data = load_csv_data()
    subjects = set(item['SUBJECT'] for item in data if item['BRANCH'] == branch)
    return jsonify(list(subjects))

@app.route('/get_units/<branch>/<subject>')
def get_units(branch, subject):
    data = load_csv_data()
    units = sorted(set(item['UNIT'] for item in data if item['BRANCH'] == branch and item['SUBJECT'] == subject))
    return jsonify(list(units))

@app.route('/get_videos/<branch>/<subject>/<unit>')
def get_videos(branch, subject, unit):
    data = load_csv_data()
    videos = [item for item in data if item['BRANCH'] == branch and item['SUBJECT'] == subject and item['UNIT'] == unit]
    return jsonify(videos)

@app.route('/video_player')
def video_player():
    video_url = request.args.get('video_url')  # Get the video URL from the query string
    return render_template('video_player.html', video_url=video_url)

@app.route('/alumni')
def alumni():
    alumni_data = pd.read_csv('alumni_data.csv')
    alumni_list = alumni_data.to_dict(orient='records')
    return render_template('alumni.html', alumni_list=alumni_list)

# Load quiz data from CSV
def load_quiz_data():
    with open("quiz_data.csv", "r") as file:
        reader = csv.DictReader(file, delimiter="\t")
        return [row for row in reader]


@app.route('/get_video_progress/<username>')
def get_video_progress(username):
    conn = sqlite3.connect('video_library.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT video_name, video_url, status, timestamp
        FROM video_progress
        WHERE username = ?
    ''', (username,))   
    progress = cursor.fetchall()
    conn.close()

    return jsonify([{'video_name': row[0], 'video_url': row[1], 'status': row[2], 'timestamp': row[3]} for row in progress])

@app.route('/store_video_progress', methods=['POST'])
def store_video_progress():
    try:
        data = request.get_json()  # Use get_json to parse JSON payload
        username = data['username']
        video_name = data['video_name']
        video_url = data['video_url']
        branch = data['branch']
        subject = data['subject']
        unit = data['unit']

        status = 'Completed'

        # Store in database
        conn = sqlite3.connect('video_library.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO video_progress (username, video_name, video_url, branch, subject, unit, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, video_name, video_url, branch, subject, unit, status))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Progress saved successfully!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mcq_test', methods=["GET", "POST"])
def mcq_test():
    
    api = request.args.get('branch')
    branch, subject, unit = api.split(',')

    quiz_data = load_quiz_data()

    processed_data = []

    # Iterate over each entry in the list
    for entry in quiz_data:
        for key, value in entry.items():
            # Split the columns and values
            columns = key.split(',')
            values = value.split(',')

            # Create a dictionary for each question
            question_data = dict(zip(columns, values))

            # Append the processed question data to the list
            processed_data.append(question_data)

    processed_data = pd.DataFrame(processed_data)

    print(f"branch: {branch}")
    print(f"subject: {subject}")
    print(f"unit: {unit}")

    processed_data = processed_data[(processed_data['BRANCH']==branch) & (processed_data['SUBJECT']==subject) & (processed_data['UNIT']==unit)]
    processed_data = processed_data.drop(columns=['BRANCH1', 'SUBJECT', 'YEAR', 'UNIT', 'BRANCH'])

    quiz_data = processed_data.to_dict(orient="records")

    print(quiz_data)
    return render_template("quiz.html", quiz_data=quiz_data, api=api)

# @app.route('/mcq_test', methods=["GET", "POST"])
# def mcq_test():
    # quiz_data = [
    #     {'QUESTION': 'What is the main inadequacy of classical mechanics highlighted by quantum mechanics?',
    #      'OPTION A': 'It cannot explain the motion of planets',
    #      'OPTION B': 'It fails to account for the behavior of particles at atomic scales',
    #      'OPTION C': 'It does not consider gravitational forces',
    #      'OPTION D': 'It is too complex for practical applications',
    #      'ANSWER': 'It fails to account for the behavior of particles at atomic scales'},
    #     {'QUESTION': "Planck's theory of black body radiation introduced the concept of:",
    #      'OPTION A': 'Continuous energy distribution',
    #      'OPTION B': 'Quantized energy levels',
    #      'OPTION C': 'Classical wave behavior',
    #      'OPTION D': 'Thermodynamic equilibrium',
    #      'ANSWER': 'Quantized energy levels'},
    #     {'QUESTION': 'The Compton effect demonstrates:',
    #      'OPTION A': 'The wave nature of light',
    #      'OPTION B': 'The particle nature of photons',
    #      'OPTION C': 'The dual nature of electrons',
    #      'OPTION D': 'The conservation of energy',
    #      'ANSWER': 'The particle nature of photons'}
    # ]
    
    # return render_template('quiz.html', quiz_data=quiz_data)

# @app.route('/submit_quiz', methods=['POST'])
# def submit_quiz():
#     data = request.get_json()
#     score = data.get("score")
#     answers = data.get("answers")

#     # # Save the result to the database (dummy example with SQLite)
#     # conn = sqlite3.connect('video_library.db')
#     # cursor = conn.cursor()
#     # cursor.execute('''CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY, score REAL)''')
#     # cursor.execute('INSERT INTO results (score) VALUES (?)', (score,))
#     # conn.commit()
#     # conn.close()

#     return jsonify({"message": "Result saved successfully!"})

@app.route('/result')
def result():
    score = request.args.get('score')  # Fetch the score from the query parameters
    api = request.args.get('api')
    branch, subject, unit = api.split(',')

    quiz_status = 'Completed'
    timestamp = datetime.now()

    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    username = session['username']  # Retrieve username from session 

    # Store in database
    conn = sqlite3.connect('video_library.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO quiz_progress (username, branch, subject, unit, quiz_status, score, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, branch, subject, unit, quiz_status, score, timestamp))
    conn.commit()
    conn.close()

    return render_template('result.html', score=score)



# @app.route("/submit_quiz", methods=["POST"])
# def submit_quiz():
#     if request.method == "POST":
#         username = request.form["username"]
#         branch = request.form["branch"]
#         subject = request.form["subject"]
#         unit = request.form["unit"]

#         questions = load_quiz_data()
#         user_answers = request.form.to_dict()
#         del user_answers["username"]
#         del user_answers["branch"]
#         del user_answers["subject"]
#         del user_answers["unit"]

#         total_questions = len(user_answers)
#         correct_answers = 0

#         for qid, user_answer in user_answers.items():
#             question = next((q for q in questions if q["QUESTION"] == qid), None)
#             if question and question["ANSWER"].strip() == user_answer.strip():
#                 correct_answers += 1

#         score = (correct_answers / total_questions) * 100

#         if score == 100:
#             conn = sqlite3.connect("database.db")
#             cursor = conn.cursor()
#             cursor.execute("""
#                 INSERT INTO scores (username, branch, subject, unit, assessment, timestamp)
#                 VALUES (?, ?, ?, ?, ?, ?)
#             """, (username, branch, subject, unit, "completed", datetime.now().isoformat()))
#             conn.commit()
#             conn.close()

#         return render_template("result.html", score=score, total_questions=total_questions, correct_answers=correct_answers)


# Load video progress data from SQLite
def load_progress_data():
    try:
        conn = sqlite3.connect('video_library.db')
        query = "SELECT * FROM video_progress"
        progress_data = pd.read_sql_query(query, conn)
        conn.close()
        return progress_data.drop_duplicates()  # Remove duplicates
    except Exception as e:
        print(f"Error loading progress data: {e}")
        return pd.DataFrame()

# Route for the dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/progress_data', methods=['GET'])
def progress_data():

    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in
    
    username = session['username']  # Retrieve username from session 

    total_data = load_csv_data()
    progress_data = load_progress_data()

    df = pd.DataFrame(total_data)

    df_filtered = df
    df_filtered = df_filtered.drop(columns=['Video URL', 'BRANCH1', 'CHANNEL', 'ID', 'YEAR'])\
        .rename(columns={'SUBJECT': 'subject', 'Video URL': 'video_url', 'TITLE': 'video_name', 'UNIT': 'unit', 'BRANCH': 'branch'})


    # 2. Total videos per subject and unit
    videos_per_subject_unit_total = (
        df_filtered.groupby(['subject', 'unit', 'branch'])['video_name'].count().reset_index(name='videos_per_subject_unit_total')
    )

    # Filter by username
    progress_data_fitered = progress_data[progress_data['username'] == username]

    progress_data_fitered = progress_data_fitered.drop(columns=['id', 'video_url', 'status'])

    df_progress = (
        progress_data_fitered.groupby(["username", "video_name", "branch", "subject", "unit"], as_index=False)
        .agg({"timestamp": "max"})
    )

    df_progress['timestamp'] = pd.to_datetime(df_progress['timestamp'])

    # 2. Total videos per subject and unit
    videos_per_subject_unit = (
        df_progress.groupby(['subject', 'unit', 'branch'])['video_name'].count().reset_index(name='videos_per_subject_unit_progress')
    )

    merged_videos = pd.merge(videos_per_subject_unit, videos_per_subject_unit_total, on=['subject', 'branch', 'unit'], how='inner')

    merged_videos_per_subject = pd.merge(videos_per_subject_unit, videos_per_subject_unit_total, on=['subject', 'branch', 'unit'], how='inner')\
        .groupby(['subject', 'branch'], as_index=False)[['videos_per_subject_unit_progress', 'videos_per_subject_unit_total']].sum()

    # Rename the columns with aliasing
    merged_videos_per_subject = merged_videos_per_subject.rename(columns={
        'videos_per_subject_unit_progress': 'videos_per_subject_unit_progress_subject',
        'videos_per_subject_unit_total': 'videos_per_subject_unit_total_subject'
    })

    merged_videos['progress_percentage_unit'] = (merged_videos['videos_per_subject_unit_progress'] / merged_videos['videos_per_subject_unit_total']) * 100
    merged_videos_per_subject['progress_percentage_subject'] = (merged_videos_per_subject['videos_per_subject_unit_progress_subject'] / merged_videos_per_subject['videos_per_subject_unit_total_subject']) * 100

    # # Step 1: Merge the subject progress with the unit progress
    merged_df = pd.merge(merged_videos, merged_videos_per_subject, on=['subject', 'branch'], suffixes=('_subject', '_unit'))

    # Step 2: Initialize a dictionary to store the results by branch
    branch_dict = {}

    # Step 3: Group by 'branch' and 'subject', and create a dictionary of unit progress
    for (subject, branch), group in merged_df.groupby(['subject', 'branch']):
        unit_progress = group[['unit', 'progress_percentage_unit']].to_dict(orient='records')
        
        subject_data = {
            'SUBJECT': subject,
            'progress_percentage': group['progress_percentage_subject'].iloc[0],  # Same for all units
            'unit_progress': unit_progress
        }
        
        # If branch already exists in the dictionary, append the subject
        if branch in branch_dict:
            branch_dict[branch]['subjects'].append(subject_data)
        else:
            # Otherwise, create a new entry for the branch
            branch_dict[branch] = {
                'branch': branch,
                'subjects': [subject_data]
            }

    # Convert the dictionary to a list for the final result
    result = list(branch_dict.values())

    print(result)
    return jsonify(result)


# @app.route('/progress_data', methods=['GET'])
# def progress_data():
#     print("progress_data API called")
#     return jsonify(
#   [
#     {
#         "branch": "CS",
#         "subjects": [
#             { 
#                 "SUBJECT": "Math", 
#                 "progress_percentage": 80,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 80 },
#                     { "unit": "Unit 2", "progress_percentage": 75 },
#                     { "unit": "Unit 3", "progress_percentage": 85 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Science", 
#                 "progress_percentage": 75,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 70 },
#                     { "unit": "Unit 2", "progress_percentage": 80 },
#                     { "unit": "Unit 3", "progress_percentage": 78 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "History", 
#                 "progress_percentage": 70,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 65 },
#                     { "unit": "Unit 2", "progress_percentage": 72 },
#                     { "unit": "Unit 3", "progress_percentage": 75 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Physics", 
#                 "progress_percentage": 85,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 80 },
#                     { "unit": "Unit 2", "progress_percentage": 85 },
#                     { "unit": "Unit 3", "progress_percentage": 90 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Chemistry", 
#                 "progress_percentage": 78,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 75 },
#                     { "unit": "Unit 2", "progress_percentage": 80 },
#                     { "unit": "Unit 3", "progress_percentage": 82 }
#                 ]
#             }
#         ],
#         "totals": {
#             "total_videos": 100,
#             "completed_videos": 80
#         },
#         "daily_progress": [
#             { "date": "2024-01-01", "Math": 80, "Science": 75, "History": 70, "Physics": 85, "Chemistry": 78 },
#             { "date": "2024-01-02", "Math": 82, "Science": 77, "History": 72, "Physics": 86, "Chemistry": 80 },
#             { "date": "2024-01-03", "Math": 84, "Science": 79, "History": 74, "Physics": 87, "Chemistry": 82 },
#             { "date": "2024-01-04", "Math": 86, "Science": 81, "History": 76, "Physics": 88, "Chemistry": 84 }
#         ],
#         "weekly_progress": [
#             { "week_start": "2024-01-01", "Math": 80, "Science": 75, "History": 70, "Physics": 85, "Chemistry": 78 },
#             { "week_start": "2024-01-08", "Math": 85, "Science": 80, "History": 75, "Physics": 90, "Chemistry": 83 }
#         ],
#         "monthly_progress": [
#             { "month": "January", "Math": 85, "Science": 80, "History": 75, "Physics": 90, "Chemistry": 85 }
#         ]
#     },
#     {
#         "branch": "IT",
#         "subjects": [
#             { 
#                 "SUBJECT": "Math", 
#                 "progress_percentage": 85,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 85 },
#                     { "unit": "Unit 2", "progress_percentage": 87 },
#                     { "unit": "Unit 3", "progress_percentage": 90 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Science", 
#                 "progress_percentage": 70,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 68 },
#                     { "unit": "Unit 2", "progress_percentage": 72 },
#                     { "unit": "Unit 3", "progress_percentage": 75 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "History", 
#                 "progress_percentage": 65,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 60 },
#                     { "unit": "Unit 2", "progress_percentage": 67 },
#                     { "unit": "Unit 3", "progress_percentage": 70 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Physics", 
#                 "progress_percentage": 88,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 85 },
#                     { "unit": "Unit 2", "progress_percentage": 89 },
#                     { "unit": "Unit 3", "progress_percentage": 92 }
#                 ]
#             },
#             { 
#                 "SUBJECT": "Chemistry", 
#                 "progress_percentage": 80,
#                 "unit_progress": [
#                     { "unit": "Unit 1", "progress_percentage": 75 },
#                     { "unit": "Unit 2", "progress_percentage": 78 },
#                     { "unit": "Unit 3", "progress_percentage": 84 }
#                 ]
#             }
#         ],
#         "totals": {
#             "total_videos": 120,
#             "completed_videos": 90
#         },
#         "daily_progress": [
#             { "date": "2024-01-01", "Math": 85, "Science": 70, "History": 65, "Physics": 88, "Chemistry": 80 },
#             { "date": "2024-01-02", "Math": 87, "Science": 72, "History": 67, "Physics": 89, "Chemistry": 82 },
#             { "date": "2024-01-03", "Math": 89, "Science": 74, "History": 69, "Physics": 90, "Chemistry": 84 },
#             { "date": "2024-01-04", "Math": 91, "Science": 76, "History": 71, "Physics": 92, "Chemistry": 86 }
#         ],
#         "weekly_progress": [
#             { "week_start": "2024-01-01", "Math": 85, "Science": 70, "History": 65, "Physics": 88, "Chemistry": 80 },
#             { "week_start": "2024-01-08", "Math": 90, "Science": 75, "History": 70, "Physics": 92, "Chemistry": 85 }
#         ],
#         "monthly_progress": [
#             { "month": "January", "Math": 90, "Science": 75, "History": 70, "Physics": 92, "Chemistry": 85 }
#         ]
#     }
#   ]
# )



if __name__ == '__main__':

    app.run(debug=True)
