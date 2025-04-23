import sqlite3

DATABASE = 'quiz_master.db'

# Function to initialize the database and create an admin user
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Drop tables if they exist
    c.execute('''DROP TABLE IF EXISTS scores''')
    c.execute('''DROP TABLE IF EXISTS questions''')
    c.execute('''DROP TABLE IF EXISTS quizzes''')
    c.execute('''DROP TABLE IF EXISTS chapters''')
    c.execute('''DROP TABLE IF EXISTS subjects''')
    c.execute('''DROP TABLE IF EXISTS users''')
    c.execute('''DROP TABLE IF EXISTS attempt_details''')

    # Create tables
    c.execute('''CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    full_name TEXT,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT,
                    qualification TEXT,
                    dob TEXT,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
                  )''')

    c.execute('''CREATE TABLE subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT
                  )''')

    c.execute('''CREATE TABLE chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject_id INTEGER,
                    description TEXT,
                    FOREIGN KEY (subject_id) REFERENCES subjects(id)
                  )''')

    c.execute('''CREATE TABLE quizzes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter_id INTEGER,
                    title TEXT NOT NULL,
                    date_of_quiz DATETIME,
                    time_duration INTEGER,
                    remarks TEXT,
                    duration INTEGER CHECK(duration > 0),
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
                  )''')

    c.execute('''CREATE TABLE questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quiz_id INTEGER,
                    question_statement TEXT NOT NULL,
                    option1 TEXT,
                    option2 TEXT,
                    option3 TEXT,
                    option4 TEXT,
                    correct_answer TEXT,
                    FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
                  )''')

    c.execute('''CREATE TABLE scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    quiz_id INTEGER,
                    time_stamp_of_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_scored INTEGER,
                    duration INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
                  )''')
    
    c.execute('''CREATE TABLE attempt_details (
                        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        score_id INTEGER,
                        question_id INTEGER,
                        user_answer TEXT,
                        FOREIGN KEY (score_id) REFERENCES scores(id),
                        FOREIGN KEY (question_id) REFERENCES questions(id)
                )''')

    # Add admin if not already present
    c.execute('SELECT * FROM users WHERE email = "admin@example.com"')
    if not c.fetchone():
        c.execute('''INSERT INTO users (username, password, email, full_name, qualification, dob, role)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''', 
              ('Admin', 'admin_password', 'admin@example.com', 
               'Quiz Master', 'Administrator', '1990-01-01', 'admin'))
        print('Admin user created!')

    # Insert sample subjects
    c.execute('''INSERT INTO subjects (name, description) VALUES 
                 ('Mathematics', 'Mathematics fundamentals'),
                 ('Science', 'Basic science concepts')''')

    # Insert sample chapters
    c.execute('''INSERT INTO chapters (title, subject_id, description) VALUES 
                 ('Algebra', 1, 'Introduction to Algebra'),
                 ('Geometry', 1, 'Basic Geometry'),
                 ('Physics', 2, 'Fundamentals of Physics'),
                 ('Chemistry', 2, 'Chemical Reactions')''')

    # Insert sample quizzes
    c.execute('''INSERT INTO quizzes (chapter_id, title, date_of_quiz, time_duration, remarks, duration) VALUES 
                 (1, 'Algebra Basics', '2025-04-14T10:00', 1800, 'Basic algebra test', 30),
                 (2, 'Geometry Quiz', '2025-04-14T11:00', 2700, 'Geometry fundamentals', 45),
                 (3, 'Physics Quiz', '2025-04-14T12:00', 2400, 'Physics concepts', 40),
                 (4, 'Chemistry Test', '2025-04-14T13:00', 3000, 'Chemical reactions test', 50)''')

    # Insert sample questions
    c.execute('''INSERT INTO questions (quiz_id, question_statement, option1, option2, option3, option4, correct_answer) VALUES
                (1, 'What is 2 + 2?', '3', '4', '5', '6', '4'),
                (1, 'Solve for x: 3x = 9', '2', '3', '4', '5', '3'),
                (2, 'What is the sum of angles in a triangle?', '90', '120', '180', '360', '180'),
                (2, 'Which shape has four equal sides?', 'Triangle', 'Rectangle', 'Square', 'Pentagon', 'Square'),
                (3, 'What is Newton''s Second Law?', 'F=ma', 'E=mc²', 'PV=nRT', 'V=IR', 'F=ma'),
                (3, 'What is the unit of force?', 'Joule', 'Watt', 'Newton', 'Pascal', 'Newton'),
                (4, 'What is the chemical formula for water?', 'H2O', 'CO2', 'NaCl', 'O2', 'H2O'),
                (4, 'Which gas is used in respiration?', 'Oxygen', 'Nitrogen', 'Hydrogen', 'Carbon dioxide', 'Oxygen');'''
              )
    
    conn.commit()
    conn.close()
    print('Database initialized successfully!')

if __name__ == '__main__':
    init_db()
