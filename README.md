
# 🎓 Quiz Master App - MAD1 IITM BS

A full-featured, multi-user **exam preparation platform** built with **Flask**, **Jinja2**, **SQLite**, and **Bootstrap**. Designed for students to test their knowledge and for admins to manage quizzes and track performance effectively.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg) ![Flask](https://img.shields.io/badge/Flask-Framework-lightgrey) ![SQLite](https://img.shields.io/badge/SQLite-DB-green)

---

## Features

✅ Admin Dashboard:  
- Create, edit, and delete users, subjects, chapters, quizzes, and MCQs  
- Assign quiz durations and availability windows  
- View summary charts for performance insights  

✅ User Portal:  
- Register and login securely  
- Attempt quizzes based on subject/chapter  
- View detailed score history  

---

## Prerequisites

- Python 3.x  
- `venv` (Python Virtual Environment)  
- SQLite (bundled with Python)

---

## Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/Quiz_Master_App_MAD1.git
cd Quiz_Master_App_MAD1
```

### 2️⃣ Create and Activate Virtual Environment
```bash
python -m venv venv
```

#### On Windows:
```bash
venv\Scripts\activate
```
#### On macOS/Linux:
```bash
source venv/bin/activate
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Initialize the Database
```bash
python init_db.py
```

### 5️⃣ Start the Application
```bash
python app.py
```

Then open your browser and visit:  
📍 `http://127.0.0.1:5000/`

---

## Troubleshooting

- **Missing Packages?**  
  Run:
  ```bash
  pip install -r requirements.txt
  ```

- **Database Issues?**  
  Delete `quiz.db` and reinitialize:
  ```bash
  rm quiz_master.db
  python init_db.py
  ```

- **Changes Not Appearing?**  
  Restart the server:
  ```bash
  python app.py
  ```

---

## 📁 Folder Structure
```
Quiz_Master_App_MAD1/
│
├── app.py
├── init_db.py
├── requirements.txt
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   └── ...
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── quiz.db
└── README.md
```

---

## Developed By

**`Akshay KS`**

---
