from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import time
from datetime import datetime

app = Flask(__name__)

# app.secret_key = 'your_secret_key'
app.secret_key = 'e6b8f4a1c9d14f38a2be7d3b51c8ea51a7c4d18b6e9a90c8e24e2b1c5a89f7cd'

DATABASE = 'quiz_master.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

# Auth routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        # Check if passwords match
        if password != confirm_password:
            error = "Passwords do not match. Please re-enter."
            return render_template('register.html', error=error)
        
        conn = get_db_connection()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()
        
        if existing_user:
            error = "Username or Email already taken. Please choose different credentials."
            conn.close()
            return render_template('register.html', error=error)
        
        conn.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)', 
                     (username, email, password, 'user'))
        conn.commit()
        conn.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user is None:
            flash("User not found. Please register.", "danger")
            return render_template('login.html')
        
        if user['password'] != password:
            flash("Incorrect password. Please try again.", "danger")
            return render_template('login.html')
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']

        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch subjects and chapters for additional dashboard details
    subjects = cur.execute('SELECT * FROM subjects').fetchall()
    chapters = cur.execute("SELECT * FROM chapters").fetchall()

    # Get total quizzes count
    cur.execute("SELECT COUNT(*) FROM quizzes")
    total_quizzes = cur.fetchone()[0]

    # Get quiz IDs attempted by the user
    cur.execute("SELECT DISTINCT quiz_id FROM scores WHERE user_id = ?", (user_id,))
    attempted_quiz_ids = {row[0] for row in cur.fetchall()}  

    # Get all quizzes
    quizzes = cur.execute('SELECT * FROM quizzes').fetchall()

    # Separate quizzes into completed and non-attempted
    completed_quizzes = [quiz for quiz in quizzes if quiz['id'] in attempted_quiz_ids]
    non_attempted_quizzes = [quiz for quiz in quizzes if quiz['id'] not in attempted_quiz_ids]

    # Separate non-attempted quizzes into available (start time passed) and upcoming (start time in future)
    now = datetime.now()
    final_available = []
    upcoming_quizzes = []
    for quiz in non_attempted_quizzes:
        # Convert quiz date from string to datetime using ISO 8601 format
        quiz_datetime = datetime.strptime(quiz['date_of_quiz'], "%Y-%m-%dT%H:%M")
        if quiz_datetime <= now:
            final_available.append(quiz)
        else:
            upcoming_quizzes.append(quiz)

    quizzes_attempted = len(attempted_quiz_ids)

    # Get user's recent quiz history (latest 5 attempts)
    cur.execute("""
        SELECT quizzes.id AS quiz_id, quizzes.title AS quiz_title, scores.total_scored, scores.time_stamp_of_attempt,
               (SELECT COUNT(*) FROM questions WHERE quiz_id = quizzes.id) AS total_questions
        FROM scores
        JOIN quizzes ON scores.quiz_id = quizzes.id
        WHERE scores.user_id = ?
        ORDER BY datetime(scores.time_stamp_of_attempt) DESC
        LIMIT 5
    """, (user_id,))
    recent_attempts = cur.fetchall()

    # Get user rankings based on total score
    cur.execute("""
        SELECT user_id, SUM(total_scored) as total_score
        FROM scores
        GROUP BY user_id
        ORDER BY total_score DESC
    """)
    ranks = cur.fetchall()
    user_rank = 1 + next((i for i, row in enumerate(ranks) if row[0] == user_id), len(ranks) if ranks else 0)

    conn.close()

    return render_template('dashboard.html', 
                           subjects=subjects,
                           chapters=chapters,
                           available_quizzes=final_available, 
                           upcoming_quizzes=upcoming_quizzes,
                           completed_quizzes=completed_quizzes,
                           recent_attempts=recent_attempts,
                           total_quizzes=total_quizzes,
                           quizzes_attempted=quizzes_attempted,
                           user_rank=user_rank,
                           total_participants=len(ranks))

# User Route
# Leaderboard
@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_username = session.get('username')
    conn = get_db_connection()
    # Aggregate total scores per user
    scores = conn.execute('''
        SELECT users.username, SUM(scores.total_scored) as total_score
        FROM scores
        JOIN users ON scores.user_id = users.id
        WHERE users.role = 'user'
        GROUP BY users.username
        ORDER BY total_score DESC
    ''').fetchall()

    # Convert result to list for indexing
    scores_list = list(scores)
    total_participants = len(scores_list)
    user_rank = next((i + 1 for i, row in enumerate(scores_list) if row['username'] == current_username), None)
    conn.close()
    
    return render_template('leaderboard.html', scores=scores_list, current_username=current_username, user_rank=user_rank, total_participants=total_participants)

# User - Profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user:
        conn.close()
        flash("User not found!", "danger")
        return redirect(url_for('login'))
    
    scores = conn.execute('''
        SELECT quizzes.title AS quiz_name, scores.total_scored, scores.time_stamp_of_attempt AS attempt_date 
        FROM scores 
        JOIN quizzes ON scores.quiz_id = quizzes.id 
        WHERE scores.user_id = ? 
        ORDER BY scores.time_stamp_of_attempt DESC
    ''', (session['user_id'],)).fetchall()

    attempts = conn.execute('''
        SELECT quizzes.title AS quiz_name, scores.time_stamp_of_attempt AS attempt_date, quizzes.duration 
        FROM scores 
        JOIN quizzes ON scores.quiz_id = quizzes.id 
        WHERE scores.user_id = ? 
        ORDER BY scores.time_stamp_of_attempt DESC
    ''', (session['user_id'],)).fetchall()

    quiz_titles = [score['quiz_name'] for score in scores]  
    quiz_scores = [score['total_scored'] for score in scores]

    conn.close()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('login'))

    return render_template('profile.html', user=user, scores=scores, attempts=attempts, quiz_titles=quiz_titles, quiz_scores=quiz_scores)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        email = request.form.get('email')
        full_name = request.form.get('full_name', '')
        qualification = request.form.get('qualification', '')
        dob = request.form.get('dob', '')

        conn.execute('''
            UPDATE users 
            SET email = ?, full_name = ?, qualification = ?, dob = ? 
            WHERE id = ?
        ''', (email, full_name, qualification, dob, session['user_id']))
        
        conn.commit()
        conn.close()

        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    conn.close()
    return render_template('edit_profile.html', user=user)

@app.route('/quizzes')
def view_quizzes():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    subjects = cur.execute("SELECT * FROM subjects").fetchall()
    chapters = cur.execute("SELECT * FROM chapters").fetchall()
    all_quizzes = cur.execute("SELECT * FROM quizzes").fetchall()
    
    # Get attempted quiz IDs for the current user
    attempted_quiz_ids = {row[0] for row in cur.execute("SELECT DISTINCT quiz_id FROM scores WHERE user_id = ?", (user_id,)).fetchall()}
    
    # Separate quizzes into attempted and non-attempted
    attempted_quizzes = [dict(quiz) for quiz in all_quizzes if quiz['id'] in attempted_quiz_ids]
    non_attempted_quizzes = [dict(quiz) for quiz in all_quizzes if quiz['id'] not in attempted_quiz_ids]
    
    now = datetime.now()
    available_quizzes = []
    upcoming_quizzes = []
    
    for quiz in non_attempted_quizzes:
        try:
            # Try ISO 8601 format first
            quiz_datetime = datetime.strptime(quiz['date_of_quiz'], "%Y-%m-%dT%H:%M")
        except ValueError:
            # Fallback to space-separated format
            quiz_datetime = datetime.strptime(quiz['date_of_quiz'], "%Y-%m-%d %H:%M")
        if quiz_datetime <= now:
            available_quizzes.append(quiz)
        else:
            upcoming_quizzes.append(quiz)
    
    total_quizzes = len(all_quizzes)
    total_attempted = len(attempted_quizzes)
    total_available = len(available_quizzes)
    
    # Group chapters by subject_id
    chapters_by_subject = {}
    for chapter in chapters:
        chapters_by_subject.setdefault(chapter['subject_id'], []).append(dict(chapter))
    
    # Group available quizzes by chapter_id
    quizzes_by_chapter = {}
    for quiz in available_quizzes:
        quizzes_by_chapter.setdefault(quiz['chapter_id'], []).append(dict(quiz))
    
    subjects_list = []
    for subject in subjects:
        subj = dict(subject)
        subj_chapters = chapters_by_subject.get(subj['id'], [])
        for chapter in subj_chapters:
            chapter['quizzes'] = quizzes_by_chapter.get(chapter['id'], [])
        subj['chapters'] = subj_chapters
        subjects_list.append(subj)
    
    conn.close()
    
    return render_template('view_quizzes.html',
                           subjects=subjects_list,
                           attempted_quizzes=attempted_quizzes,
                           available_quizzes=available_quizzes,
                           upcoming_quizzes=upcoming_quizzes,
                           total_quizzes=total_quizzes,
                           total_attempted=total_attempted,
                           total_available=total_available)

# View-attempts
@app.route('/view_attempts')
def view_attempts():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    attempts = conn.execute('''
        SELECT quizzes.id AS quiz_id, quizzes.title AS quiz_name, scores.total_scored, 
               scores.time_stamp_of_attempt AS attempt_date, quizzes.duration 
        FROM scores 
        JOIN quizzes ON scores.quiz_id = quizzes.id 
        WHERE scores.user_id = ? 
        ORDER BY scores.time_stamp_of_attempt DESC
    ''', (session['user_id'],)).fetchall()

    formatted_attempts = []
    for attempt in attempts:
        try:
            # Assuming the timestamp is in "YYYY-MM-DD HH:MM:SS" format
            dt = datetime.strptime(attempt['attempt_date'], "%Y-%m-%d %H:%M:%S")
            formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            formatted_date = attempt['attempt_date']
        formatted_attempts.append({
            "quiz_id": attempt["quiz_id"],
            "quiz_name": attempt["quiz_name"],
            "total_scored": attempt["total_scored"],
            "attempt_date": formatted_date,
            "duration": attempt["duration"]
        })

    conn.close()
    return render_template('view_attempts.html', attempts=formatted_attempts)

@app.route('/attempt_quiz/<int:quiz_id>', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()
    conn.close()

    if request.method == 'POST':
        score = 0
        start_time_str = request.form.get('start_time')
        if not start_time_str:
            return render_template('attempt_quiz.html', quiz=quiz, questions=questions, error="Start time is missing. Please try again.")
        
        start_time = float(start_time_str)
        end_time = time.time()
        duration_taken = round((end_time - start_time) / 60, 2)

        # Collect user answers and calculate score
        user_answers_dict = {}
        for question in questions:
            user_answer = request.form.get(f"question_{question['id']}", "Not Attempted")
            user_answers_dict[question['id']] = user_answer
            if user_answer == question['correct_answer']:
                score += 1

        # Insert overall attempt into scores table and get the score_id
        conn = get_db_connection()
        cur = conn.execute(
            'INSERT INTO scores (user_id, quiz_id, time_stamp_of_attempt, total_scored, duration) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)', 
            (session['user_id'], quiz_id, score, duration_taken)
        )
        conn.commit()
        score_id = cur.lastrowid 

        for question in questions:
            answer = user_answers_dict.get(question['id'], "Not Attempted")
            conn.execute(
                'INSERT INTO attempt_details (score_id, question_id, user_answer) VALUES (?, ?, ?)',
                (score_id, question['id'], answer)
            )
        conn.commit()
        conn.close()
        
        return render_template('attempt_quiz.html', quiz=quiz, questions=questions, score=score, total=len(questions), duration_taken=duration_taken)

    return render_template('attempt_quiz.html', quiz=quiz, questions=questions, start_time=time.time(), score=None)

@app.route('/download_analysis/<int:quiz_id>')
def download_analysis(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()

    attempt = conn.execute(
        'SELECT * FROM scores WHERE user_id = ? AND quiz_id = ? ORDER BY time_stamp_of_attempt DESC LIMIT 1',
        (session['user_id'], quiz_id)
    ).fetchone()

    if not attempt:
        conn.close()
        return redirect(url_for('dashboard'))

    score = attempt['total_scored']
    duration = attempt['duration']
    score_id = attempt['id']

    attempt_details = conn.execute(
        'SELECT * FROM attempt_details WHERE score_id = ?', (score_id,)
    ).fetchall()
    conn.close()

    user_answers = {}
    for detail in attempt_details:
        user_answers[detail['question_id']] = detail['user_answer']

    return render_template('analysis.html', quiz=quiz, questions=questions, score=score, duration=duration, user_answers=user_answers)

# Admin
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    total_subjects = conn.execute('SELECT COUNT(*) FROM subjects').fetchone()[0]
    total_chapters = conn.execute('SELECT COUNT(*) FROM chapters').fetchone()[0]
    total_quizzes = conn.execute('SELECT COUNT(*) FROM quizzes').fetchone()[0]
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    subjects = conn.execute('SELECT * FROM subjects').fetchall()
    chapters = conn.execute('SELECT * FROM chapters').fetchall()
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()
    users = conn.execute("SELECT username, email FROM users WHERE role = 'user'").fetchall()
    conn.close()

    chapters_by_subject = {}
    for chapter in chapters:
        subject_id = chapter['subject_id']
        chapters_by_subject.setdefault(subject_id, []).append(dict(chapter))

    quizzes_by_chapter = {}
    for quiz in quizzes:
        chapter_id = quiz['chapter_id']
        quizzes_by_chapter.setdefault(chapter_id, []).append(dict(quiz))

    # Attach chapters and quizzes to each subject.
    subjects_list = []
    for subject in subjects:
        subj = dict(subject)
        subj_chapters = chapters_by_subject.get(subj['id'], [])
        # For each chapter, attach its quizzes.
        for chapter in subj_chapters:
            chapter['quizzes'] = quizzes_by_chapter.get(chapter['id'], [])
        subj['chapters'] = subj_chapters
        subjects_list.append(subj)

    return render_template('admin_dashboard.html', 
                           total_subjects=total_subjects, 
                           total_chapters=total_chapters,
                           total_quizzes=total_quizzes, 
                           total_users=total_users, 
                           subjects=subjects_list,
                           users=users)

@app.route('/admin/profile')
def admin_profile():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    subjects = conn.execute('SELECT * FROM subjects').fetchall()
    chapters = conn.execute('SELECT * FROM chapters').fetchall()
    quizzes = conn.execute('SELECT * FROM quizzes').fetchall()
    # Calculate recent quizzes, e.g., last 5 quizzes ordered by date_of_quiz descending:
    recent_quizzes = conn.execute('SELECT * FROM quizzes ORDER BY date_of_quiz DESC LIMIT 5').fetchall()
    
    # Query for user performance
    user_performance = conn.execute('''
        SELECT u.id, u.username, u.email,
               COUNT(s.id) AS attempts,
               ROUND(AVG(s.total_scored), 2) AS avg_score,
               COALESCE(SUM(s.total_scored), 0) AS total_score
        FROM users u
        LEFT JOIN scores s ON u.id = s.user_id
        WHERE u.role = 'user'
        GROUP BY u.id, u.username, u.email
    ''').fetchall()
    
    # Query for subject performance
    subject_performance = conn.execute('''
        SELECT sub.id, sub.name, COUNT(s.id) AS attempts, ROUND(AVG(s.total_scored),2) AS avg_score
        FROM subjects sub
        JOIN chapters ch ON sub.id = ch.subject_id
        JOIN quizzes q ON ch.id = q.chapter_id
        JOIN scores s ON q.id = s.quiz_id
        GROUP BY sub.id, sub.name
    ''').fetchall()
    
    # Process subjects, chapters, and quizzes for the quick actions section
    chapters_by_subject = {}
    for chapter in chapters:
        chapters_by_subject.setdefault(chapter['subject_id'], []).append(dict(chapter))
    
    quizzes_by_chapter = {}
    for quiz in quizzes:
        quizzes_by_chapter.setdefault(quiz['chapter_id'], []).append(dict(quiz))
    
    subjects_list = []
    for subject in subjects:
        subj = dict(subject)
        subj_chapters = chapters_by_subject.get(subj['id'], [])
        for chapter in subj_chapters:
            chapter['quizzes'] = quizzes_by_chapter.get(chapter['id'], [])
        subj['chapters'] = subj_chapters
        subjects_list.append(subj)
    
    conn.close()
    return render_template('admin_profile.html', 
                           admin=admin, 
                           subjects=subjects_list, 
                           recent_quizzes=recent_quizzes,
                           user_performance=user_performance,
                           subject_performance=subject_performance)


# Admin - User Controller
# Fetch Users
@app.route('/admin/manage_users')
def manage_users():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users WHERE username!="Admin" ').fetchall()
    conn.close()
    return render_template('manage_users.html',users=users)

# Add User
@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    username = request.form['username'].strip() 
    email = request.form['email'].strip()
    password = request.form['password'].strip()
    full_name = request.form.get('full_name', '').strip() or None
    phone = request.form.get('phone', '').strip() or None
    qualification = request.form.get('qualification', '').strip() or None
    dob = request.form.get('dob', '').strip() or None


    conn = get_db_connection()
    
    # Check if username already exists
    existing_user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                                 (username, email)).fetchone()
    if existing_user:
        conn.close()
        flash('Username already exists!', 'danger')
        return redirect(url_for('manage_users'))

    conn.execute('''
        INSERT INTO users (username, email, password, full_name, phone, qualification, dob, role) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (username, email, password, full_name, phone, qualification, dob, 'user'))
    conn.commit()
    conn.close()

    flash('User added successfully!', 'success')
    return redirect(url_for('manage_users'))

# Delete User
@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    users = conn.execute('SELECT * FROM users WHERE username!="Admin" ').fetchall()
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'danger')
    return redirect(url_for('manage_users'))

# Edit User
@app.route('/admin/edit_user/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    username = request.form['username'].strip()
    email = request.form['email'].strip()
    role = 'user'

    conn = get_db_connection()
    
    # Ensure user exists before updating
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        conn.close()
        flash('User not found!', 'danger')
        return redirect(url_for('manage_users',users=users))

    # Check if the email is used by another user
    email_exists = conn.execute(
        'SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id)
    ).fetchone()

    users = conn.execute('SELECT * FROM users WHERE username!="Admin" ').fetchall()

    if email_exists:
        conn.close()
        flash('Email already in use!', 'danger')
        return redirect(url_for('manage_users'))

    # Update user details
    conn.execute('UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?', 
                 (username, email, role, user_id))
    conn.commit()
    conn.close()

    flash('User updated successfully!', 'success')
    return redirect(url_for('manage_users'))

# Subject Controllers
# Add and Get Subjects
@app.route('/admin/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        subject_name = request.form['name'].strip()
        subject_description = request.form['description'].strip()

        # Check if subject name already exists
        existing_subject = conn.execute('SELECT id FROM subjects WHERE name = ?', (subject_name,)).fetchone()
        if existing_subject:
            conn.close()
            flash('Subject name already exists!', 'danger')
            return redirect(url_for('manage_subjects'))

        conn.execute('INSERT INTO subjects (name, description) VALUES (?, ?)', 
                     (subject_name, subject_description))
        conn.commit()
        flash('Subject created successfully!', 'success')

    subjects = conn.execute('SELECT * FROM subjects').fetchall()
    conn.close()
    return render_template('manage_subjects.html', subjects=subjects)

# Edit Subjects
@app.route('/admin/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
def edit_subject(subject_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    name = request.form['name'].strip()
    description = request.form['description'].strip()

    conn = get_db_connection()

    # Ensure subject exists before updating
    subject = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    if not subject:
        conn.close()
        flash('Subject not found!', 'danger')
        return redirect(url_for('manage_subjects'))

    # Check if new subject name is already taken by another subject
    name_exists = conn.execute(
        'SELECT id FROM subjects WHERE name = ? AND id != ?', (name, subject_id)
    ).fetchone()

    if name_exists:
        conn.close()
        flash('Subject name already exists!', 'danger')
        return redirect(url_for('manage_subjects'))

    conn.execute('UPDATE subjects SET name = ?, description = ? WHERE id = ?', 
                 (name, description, subject_id))
    conn.commit()
    conn.close()

    flash('Subject updated successfully!', 'success')
    return redirect(url_for('manage_subjects'))

# Delete Subject
@app.route('/admin/delete_subject/<int:subject_id>')
def delete_subject(subject_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    subject = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    if not subject:
        conn.close()
        flash('Subject not found!', 'danger')
        return redirect(url_for('manage_subjects'))

    conn.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
    conn.commit()
    conn.close()

    flash('Subject deleted successfully!', 'success')
    return redirect(url_for('manage_subjects'))


# Chapter Controllers
# Add and Get Chapters
@app.route('/admin/manage_chapters/<int:subject_id>', methods=['GET', 'POST'])
def manage_chapters(subject_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        chapter_title = request.form['title'].strip()
        chapter_description = request.form['description'].strip()

        # Check if chapter title already exists for this subject
        existing_chapter = conn.execute(
            'SELECT id FROM chapters WHERE title = ? AND subject_id = ?', 
            (chapter_title, subject_id)
        ).fetchone()
        
        if existing_chapter:
            conn.close()
            flash('Chapter title already exists!', 'danger')
            return redirect(url_for('manage_chapters', subject_id=subject_id))
        
        conn.execute(
            'INSERT INTO chapters (subject_id, title, description) VALUES (?, ?, ?)', 
            (subject_id, chapter_title, chapter_description)
        )
        conn.commit()
        flash('Chapter added successfully!', 'success')

    chapters = conn.execute(
        'SELECT * FROM chapters WHERE subject_id = ?', (subject_id,)
    ).fetchall()
    conn.close()

    return render_template('manage_chapters.html', chapters=chapters, subject_id=subject_id)

# Edit Chapter
@app.route('/admin/edit_chapter/<int:chapter_id>', methods=['GET', 'POST'])
def edit_chapter(chapter_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    chapter = conn.execute(
        'SELECT * FROM chapters WHERE id = ?', (chapter_id,)
    ).fetchone()

    if not chapter:
        conn.close()
        flash('Chapter not found!', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()

        # Check if new title already exists under the same subject
        title_exists = conn.execute(
            'SELECT id FROM chapters WHERE title = ? AND subject_id = ? AND id != ?', 
            (title, chapter['subject_id'], chapter_id)
        ).fetchone()

        if title_exists:
            conn.close()
            flash('Chapter title already exists!', 'danger')
            return redirect(url_for('manage_chapters', subject_id=chapter['subject_id']))
        
        conn.execute(
            'UPDATE chapters SET title = ?, description = ? WHERE id = ?', 
            (title, description, chapter_id)
        )
        conn.commit()
        conn.close()

        flash('Chapter updated successfully!', 'success')
        return redirect(url_for('manage_chapters', subject_id=chapter['subject_id']))

    return render_template('edit_chapter.html', chapter=chapter)

# Delete Chapter
@app.route('/admin/delete_chapter/<int:chapter_id>')
def delete_chapter(chapter_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    chapter = conn.execute(
        'SELECT subject_id FROM chapters WHERE id = ?', (chapter_id,)
    ).fetchone()
    if not chapter:
        conn.close()
        flash('Chapter not found!', 'danger')
        return redirect(url_for('admin_dashboard'))

    subject_id = chapter['subject_id']
    conn.execute('DELETE FROM chapters WHERE id = ?', (chapter_id,))
    conn.commit()
    conn.close()

    flash('Chapter deleted successfully!', 'success')
    return redirect(url_for('manage_chapters', subject_id=subject_id))


# Quiz Controllers
# Add and Get Quizzes
@app.route('/admin/manage_quizzes/<int:chapter_id>', methods=['GET', 'POST'])
def manage_quizzes(chapter_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        date_of_quiz = request.form['date_of_quiz']
        time_duration = request.form['time_duration']
        remarks = request.form['remarks'] or None
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO quizzes (chapter_id, title, date_of_quiz, time_duration, remarks , duration) VALUES (?, ?, ?, ?, ?,?)', 
            (chapter_id, title, date_of_quiz, time_duration, remarks,int(time_duration)//60)
        )
        conn.commit()
        conn.close()
        flash('Quiz added successfully!', 'success')
        return redirect(url_for('manage_quizzes', chapter_id=chapter_id))

    conn = get_db_connection()
    quizzes = conn.execute('''SELECT quizzes.*, chapters.title AS chapter_title 
        FROM quizzes 
        JOIN chapters ON quizzes.chapter_id = chapters.id 
        WHERE quizzes.chapter_id = ?''', (chapter_id,)).fetchall()
    conn.close()
    return render_template('manage_quizzes.html', quizzes=quizzes, chapter_id=chapter_id)

# Edit Quiz
@app.route('/admin/edit_quiz/<int:quiz_id>', methods=['POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    quiz = conn.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    if not quiz:
        conn.close()
        flash('Quiz not found!', 'danger')
        return redirect(url_for('manage_quizzes'))

    name = request.form['title'].strip()
    duration = request.form['time_duration'].strip()

    conn.execute('UPDATE quizzes SET title = ?, time_duration = ? WHERE id = ?', 
                 (name, duration, quiz_id))
    conn.commit()
    conn.close()

    flash('Quiz updated successfully!', 'success')
    return redirect(url_for('manage_quizzes', chapter_id=quiz['chapter_id']))

# Delete Quizzes
@app.route('/admin/delete_quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    quiz = conn.execute('SELECT chapter_id FROM quizzes WHERE id = ?', (quiz_id,)).fetchone()
    
    if not quiz:
        conn.close()
        flash('Quiz not found!', 'danger')
        return redirect(url_for('admin_dashboard'))  

    chapter_id = quiz['chapter_id'] 
    conn.execute('DELETE FROM quizzes WHERE id = ?', (quiz_id,))
    conn.commit()
    conn.close()
    flash('Quiz deleted successfully!', 'danger')
    return redirect(url_for('manage_quizzes', chapter_id=chapter_id))

# Question Controllers
# Add and Get Questions
@app.route('/admin/manage_questions/<int:quiz_id>', methods=['GET', 'POST'])
def manage_questions(quiz_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        question_statement = request.form['question_statement']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        correct_answer = request.form['correct_answer']
        conn = get_db_connection()
        conn.execute('INSERT INTO questions (quiz_id, question_statement, option1, option2, option3, option4, correct_answer) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                     (quiz_id, question_statement, option1, option2, option3, option4, correct_answer))
        conn.commit()
        conn.close()
        flash('Question added successfully!', 'success')
        return redirect(url_for('manage_questions', quiz_id=quiz_id))

    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions WHERE quiz_id = ?', (quiz_id,)).fetchall()
    conn.close()
    return render_template('manage_questions.html', questions=questions, quiz_id=quiz_id)

# Edit Question
@app.route('/admin/edit_question/<int:question_id>', methods=['POST'])
def edit_question(question_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    # Ensure the question exists before updating
    question = conn.execute('SELECT * FROM questions WHERE id = ?', (question_id,)).fetchone()
    if not question:
        conn.close()
        flash('Question not found!', 'danger')
        return redirect(url_for('manage_questions', quiz_id=question['quiz_id']))

    question_statement = request.form['question_statement']
    option1 = request.form['option1']
    option2 = request.form['option2']
    option3 = request.form['option3']
    option4 = request.form['option4']
    correct_answer = request.form['correct_answer']

    conn.execute(
        'UPDATE questions SET question_statement = ?, option1 = ?, option2 = ?, option3 = ?, option4 = ?, correct_answer = ? WHERE id = ?',
        (question_statement, option1, option2, option3, option4, correct_answer, question_id)
    )
    conn.commit()
    conn.close()

    flash('Question updated successfully!', 'success')
    return redirect(url_for('manage_questions', quiz_id=question['quiz_id']))

# Delete Question
@app.route('/admin/delete_question/<int:question_id>')
def delete_question(question_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()
    question = conn.execute('SELECT quiz_id FROM questions WHERE id = ?', (question_id,)).fetchone()
    if not question:
        conn.close()
        flash('Question not found!', 'danger')
        return redirect(url_for('manage_questions', quiz_id=question_id))

    conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    conn.close()

    flash('Question deleted successfully!', 'danger')
    return redirect(url_for('manage_questions', quiz_id=question['quiz_id']))

# Search Functionalities
# Search User
@app.route('/admin/search_users', methods=['GET'])
def search_users():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()
    
    with get_db_connection() as conn:
        users = conn.execute(
            "SELECT * FROM users WHERE (username LIKE ? OR email LIKE ?) AND username != 'Admin'", 
            (f"%{search_query}%", f"%{search_query}%")
        ).fetchall()
    
    return render_template('manage_users.html', users=users, search=search_query)

# Search Subject
@app.route('/admin/search_subjects', methods=['GET'])
def search_subjects():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()

    with get_db_connection() as conn:
        subjects = conn.execute(
            "SELECT * FROM subjects WHERE name LIKE ?", (f"%{search_query}%",)
        ).fetchall()

    return render_template('manage_subjects.html', subjects=subjects, search=search_query)

# Search quizzes
@app.route('/admin/search_quizzes/<int:chapter_id>', methods=['GET'])
def search_quizzes(chapter_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()

    with get_db_connection() as conn:
        quizzes = conn.execute('''
            SELECT quizzes.*, chapters.title AS chapter_title
            FROM quizzes
            JOIN chapters ON quizzes.chapter_id = chapters.id
            WHERE quizzes.chapter_id = ? AND quizzes.title LIKE ?
        ''', (chapter_id, f"%{search_query}%")).fetchall()

    return render_template('manage_quizzes.html', quizzes=quizzes, chapter_id=chapter_id, search=search_query)

# Search Chapters
@app.route('/admin/search_chapters/<int:subject_id>', methods=['GET'])
def search_chapters(subject_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()

    with get_db_connection() as conn:
        chapters = conn.execute(
            "SELECT * FROM chapters WHERE subject_id = ? AND title LIKE ?", 
            (subject_id, f"%{search_query}%")
        ).fetchall()

    return render_template('manage_chapters.html', chapters=chapters, subject_id=subject_id, search=search_query)

# Search Questions
@app.route('/admin/search_questions', methods=['GET'])
def search_questions():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    # Retrieve the quiz_id and search term from query parameters
    quiz_id = request.args.get('quiz_id', type=int)
    search_query = request.args.get('search', '').strip()

    with get_db_connection() as conn:
        questions = conn.execute(
            "SELECT * FROM questions WHERE quiz_id = ? AND question_statement LIKE ?",
            (quiz_id, f"%{search_query}%")
        ).fetchall()

    return render_template('manage_questions.html', questions=questions, quiz_id=quiz_id, search=search_query)

# View reports
@app.route('/admin/view_reports')
def view_reports():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        reports = conn.execute("""
            SELECT users.username, quizzes.title AS quiz_title, scores.total_scored, scores.time_stamp_of_attempt, scores.duration
            FROM scores
            JOIN users ON scores.user_id = users.id
            JOIN quizzes ON scores.quiz_id = quizzes.id
            ORDER BY scores.time_stamp_of_attempt DESC
        """).fetchall()

    return render_template('view_reports.html', reports=reports)

@app.route('/admin/delete_all')
def delete_all_quizzes():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db_connection()

    conn.execute('DELETE FROM quizzes')
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True,port=5001)
