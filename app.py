import os
from flask import Flask, jsonify, request, send_from_directory
from pymongo import MongoClient
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from bson import ObjectId
import json
from werkzeug.utils import secure_filename
from datetime import datetime

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

MONGO_URI = "mongodb+srv://myWeb:palli2003@cluster0.mxulqff.mongodb.net/?appName=Cluster0"
DB_NAME = "vssut_platform"

# --- GLOBAL CORS FIX ---
CORS(app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"])

bcrypt = Bcrypt(app)

# --- Database Connection ---
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    users_collection = db.users
    profiles_collection = db.profiles
    courses_collection = db.courses
    posts_collection = db.posts
    doubts_collection = db.doubts
    # --- ADDED THESE TWO LINES ---
    exams_collection = db.exams 
    exam_results_collection = db.exam_results
    # -----------------------------
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

# --- Authentication Routes ---

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    user_type = data.get('userType')
    username = data.get('username')
    password = data.get('password')

    if not user_type or not username or not password:
        return jsonify({"message": "Missing required fields"}), 400
    if users_collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists. Please login."}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "userType": user_type,
        "approved": False 
    })
    
    return jsonify({"message": "Sign up successful! Please wait for admin approval."}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_type = data.get('userType')
    username = data.get('username')
    password = data.get('password')

    # Find user
    user = users_collection.find_one({"username": username, "userType": user_type})
    
    if not user:
        return jsonify({"message": "Invalid credentials or user type."}), 401

    # Check Password
    if bcrypt.check_password_hash(user['password'], password):
        
        # --- ENFORCEMENT LOGIC ---
        # If user is NOT admin AND their approved status is False (or missing), deny login
        if user_type != 'admin' and not user.get('approved', False):
             return jsonify({"message": "Access Denied: Your account is pending Admin approval."}), 403
        # -------------------------

        return jsonify({
            "message": "Login successful!",
            "user_role": user['userType'],
            "username": user['username']
        }), 200
    else:
        return jsonify({"message": "Invalid credentials."}), 401

# --- Admin Routes ---

@app.route('/api/admin/users', methods=['GET'])
def get_all_users():
    users = list(users_collection.find({}, {"password": 0}))
    for user in users:
        if '_id' in user:
            user['_id'] = str(user['_id'])
        if 'approved' not in user:
            user['approved'] = False 
            
    return jsonify(users), 200

# Route for Admin to Add User Directly (Auto-Approved)
@app.route('/api/admin/add_user', methods=['POST'])
def admin_add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user_type = data.get('userType')

    if not username or not password or not user_type:
        return jsonify({"message": "Missing fields"}), 400
        
    if users_collection.find_one({"username": username}):
        return jsonify({"message": "Username already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "userType": user_type,
        "approved": True # Admin created users are auto-approved
    })
    
    return jsonify({"message": "User added successfully"}), 201

@app.route('/api/admin/users/<user_id>', methods=['DELETE'])
def delete_user_admin(user_id):
    try:
        users_collection.delete_one({"_id": ObjectId(user_id)})
        return jsonify({"message": "User deleted"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/api/admin/users/<user_id>/approve', methods=['POST'])
def approve_user(user_id):
    try:
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"approved": True}}
        )
        return jsonify({"message": "User approved"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# --- Profile Routes ---

@app.route('/api/profile/<username>', methods=['GET'])
def get_profile(username):
    profile = profiles_collection.find_one({"username": username}, {"_id": 0})
    if profile:
        return jsonify(profile), 200
    else:
        return jsonify({"message": "Profile not found", "username": username}), 404
    
@app.route('/api/profile/by-roll/<roll_number>', methods=['GET'])
def get_profile_by_roll(roll_number):
    profile = profiles_collection.find_one({"rollNumber": roll_number}, {"_id": 0})
    if profile:
        return jsonify(profile), 200
    else:
        return jsonify({"message": "Profile not found for this roll number"}), 404

@app.route('/api/profile/<username>', methods=['POST'])
def update_profile(username):
    profile_data = request.json
    profiles_collection.update_one(
        {"username": username},
        {"$set": profile_data},
        upsert=True
    )
    return jsonify({"message": "Profile updated successfully"}), 200

# --- Course Routes ---

@app.route('/api/courses', methods=['GET'])
def get_courses():
    teacher_username = request.args.get('teacher')
    student_roll = request.args.get('student_roll')
    
    query = {}
    
    # Filter 1: If it's a teacher, show only courses they created
    if teacher_username:
        query['creator'] = teacher_username
        
    # Filter 2: If it's a student, show only courses where their Roll Number exists in the 'students' list
    elif student_roll:
        query['students.rollNumber'] = student_roll
        
    # If neither is provided, it returns all courses (useful for Admin)
    
    courses = list(courses_collection.find(query, {"name": 1, "courseCode": 1, "students": 1, "creator": 1, "_id": 0}))
    
    response = jsonify(courses)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response, 200

@app.route('/api/courses/<course_code>/count', methods=['GET'])
def get_student_count(course_code):
    course = courses_collection.find_one({"courseCode": course_code})
    if course:
        students = course.get("students", [])
        return jsonify({"studentCount": len(students)}), 200
    else:
        return jsonify({"message": "Course not found"}), 404

@app.route('/api/courses', methods=['POST'])
def add_course():
    data = request.json
    name = data.get('name')
    course_code = data.get('courseCode')
    creator = data.get('creator')

    if not name or not course_code:
        return jsonify({"message": "Course name and code are required"}), 400

    if courses_collection.find_one({"courseCode": course_code}):
        return jsonify({"message": "Course code already exists"}), 409

    courses_collection.insert_one({
        "name": name,
        "courseCode": course_code,
        "creator": creator,
        "lectureDates": [], 
        "students": []
    })
    return jsonify({"message": "Course added successfully"}), 201

@app.route('/api/courses/<course_code>', methods=['DELETE'])
def delete_course(course_code):
    result = courses_collection.delete_one({"courseCode": course_code})
    if result.deleted_count:
        return jsonify({"message": "Course deleted successfully"}), 200
    else:
        return jsonify({"message": "Course not found"}), 404

# --- Attendance Routes ---

@app.route('/api/attendance/<course_code>', methods=['GET'])
def get_attendance_data(course_code):
    course_data = courses_collection.find_one({"courseCode": course_code})
    if course_data:
        data = {
            "students": course_data.get("students", []),
            "lectureDates": course_data.get("lectureDates", [])
        }
        response = jsonify(data)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response, 200
    else:
        return jsonify({"message": "Course not found"}), 404

@app.route('/api/attendance/<course_code>', methods=['POST'])
def save_attendance_data(course_code):
    data = request.json
    students = data.get('students')
    lecture_dates = data.get('lectureDates')

    if students is None or lecture_dates is None:
        return jsonify({"message": "Missing students or lectureDates data"}), 400

    courses_collection.update_one(
        {"courseCode": course_code},
        {"$set": {
            "students": students,
            "lectureDates": lecture_dates
        }}
    )
    return jsonify({"message": "Attendance saved successfully"}), 200

# --- Notification/Posts Routes ---

@app.route('/api/posts', methods=['POST'])
def upload_post():
    course_code = request.form.get('courseCode')
    title = request.form.get('postTitle')
    description = request.form.get('postDescription')
    file = request.files.get('fileUpload')
    post_date_str = request.form.get('postDate') 

    if not course_code or not title or not file or not post_date_str:
        return jsonify({"message": "Missing course, title, file, or date"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"message": "Invalid file name"}), 400
    
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    try:
        post_date_obj = datetime.fromisoformat(post_date_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({"message": "Invalid date format"}), 400

    post_data = {
        "courseCode": course_code,
        "courseName": request.form.get('courseName', ''),
        "title": title,
        "description": description,
        "fileName": filename,
        "fileType": file.content_type,
        "postDate": post_date_obj 
    }
    posts_collection.insert_one(post_data)
    
    return jsonify({"message": "Post uploaded successfully"}), 201

@app.route('/api/posts', methods=['GET'])
def get_posts():
    course_code = request.args.get('courseCode')
    query = {}
    if course_code:
        query = {"courseCode": course_code}
        
    posts = list(posts_collection.find(query).sort("postDate", -1))
    
    for post in posts:
        if '_id' in post:
            post['_id'] = str(post['_id'])
        if 'postDate' in post and isinstance(post['postDate'], datetime):
            post['postDate'] = post['postDate'].isoformat()
    
    response = jsonify(posts)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response, 200

@app.route('/api/posts/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    try:
        post = posts_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            return jsonify({"message": "Post not found"}), 404

        filename = post.get('fileName')
        if filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)

        posts_collection.delete_one({"_id": ObjectId(post_id)})
        return jsonify({"message": "Post deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting post: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route('/uploads/<filename>', methods=['GET'])
def get_uploaded_file(filename):
    safe_filename = secure_filename(filename)
    if not safe_filename:
        return jsonify({"message": "Invalid filename"}), 400
    return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename)


# --- DOUBTS / CHAT ROUTES ---

@app.route('/api/doubts/<course_code>', methods=['GET'])
def get_doubts(course_code):
    # Get messages for a specific course, sorted by time
    messages = list(doubts_collection.find({"courseCode": course_code}).sort("timestamp", 1))
    
    for msg in messages:
        if '_id' in msg:
            msg['_id'] = str(msg['_id'])
        if 'timestamp' in msg and isinstance(msg['timestamp'], datetime):
            msg['timestamp'] = msg['timestamp'].strftime("%Y-%m-%d %H:%M")
            
    return jsonify(messages), 200

@app.route('/api/doubts', methods=['POST'])
def post_doubt():
    data = request.json
    course_code = data.get('courseCode')
    username = data.get('username')
    role = data.get('role')
    message = data.get('message')

    if not all([course_code, username, role, message]):
        return jsonify({"message": "Missing fields"}), 400

    # --- RESTRICTION LOGIC ---
    # Python weekday(): Monday is 0, Sunday is 6.
    # We want Saturday (5) and Sunday (6).
    current_day = datetime.now().weekday()
    
    if role == 'student' and current_day not in [5, 6]:
        return jsonify({"message": "Students can only post doubts on Saturday and Sunday."}), 403

    doubt_entry = {
        "courseCode": course_code,
        "username": username,
        "role": role,
        "message": message,
        "timestamp": datetime.now()
    }
    
    doubts_collection.insert_one(doubt_entry)
    return jsonify({"message": "Message sent"}), 201

@app.route('/api/doubts/<message_id>', methods=['DELETE'])
def delete_doubt(message_id):
    try:
        doubts_collection.delete_one({"_id": ObjectId(message_id)})
        return jsonify({"message": "Message deleted"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    
# --- EXAM ROUTES ---

@app.route('/api/exams', methods=['GET'])
def get_exams():
    role = request.args.get('role')
    username = request.args.get('username')
    
    if role == 'teacher':
        # Teachers see exams they created
        exams = list(exams_collection.find({"creator": username}))
    elif role == 'student':
        # Students need to see exams for courses they are enrolled in
        # 1. Get Student Profile for Roll Number
        profile = profiles_collection.find_one({"username": username})
        if not profile or 'rollNumber' not in profile:
            return jsonify([]), 200
        
        roll_number = profile['rollNumber']
        
        # 2. Find courses student is enrolled in
        enrolled_courses = list(courses_collection.find(
            {"students.rollNumber": roll_number}, 
            {"courseCode": 1}
        ))
        course_codes = [c['courseCode'] for c in enrolled_courses]
        
        # 3. Find exams for those courses
        exams = list(exams_collection.find({"courseCode": {"$in": course_codes}}))
    else:
        exams = []

    # Format ObjectId for JSON
    for ex in exams:
        ex['_id'] = str(ex['_id'])
        
    return jsonify(exams), 200

@app.route('/api/exams', methods=['POST'])
def create_exam():
    data = request.json
    # Basic Validation
    if not data.get('courseCode') or not data.get('questions'):
        return jsonify({"message": "Missing details"}), 400
        
    exam_data = {
        "courseCode": data['courseCode'],
        "title": data['title'],
        "creator": data['creator'],
        "questions": data['questions'], # List of {question, options[], correctIndex}
        "created_at": datetime.now()
    }
    exams_collection.insert_one(exam_data)
    return jsonify({"message": "Exam created successfully"}), 201

@app.route('/api/exams/status', methods=['POST'])
def check_exam_status():
    # Check if student has already taken/locked this exam
    data = request.json
    exam_id = data.get('examId')
    username = data.get('username')
    
    result = exam_results_collection.find_one({
        "examId": exam_id,
        "studentUsername": username
    })
    
    if result:
        return jsonify({"status": result['status'], "score": result.get('score', 0)}), 200
    return jsonify({"status": "new"}), 200

@app.route('/api/exams/start', methods=['POST'])
def start_exam():
    # Mark exam as 'in-progress' so if they close window, it locks
    data = request.json
    exam_id = data.get('examId')
    username = data.get('username')
    
    # Check if already exists
    existing = exam_results_collection.find_one({"examId": exam_id, "studentUsername": username})
    if existing:
        return jsonify({"message": "Exam already started or finished"}), 400

    exam_results_collection.insert_one({
        "examId": exam_id,
        "studentUsername": username,
        "status": "in-progress",
        "score": 0
    })
    return jsonify({"message": "Exam started"}), 200

@app.route('/api/exams/submit', methods=['POST'])
def submit_exam():
    data = request.json
    exam_id = data.get('examId')
    username = data.get('username')
    answers = data.get('answers') # List of indices selected by student
    
    # 1. Fetch the actual exam to compare answers
    exam = exams_collection.find_one({"_id": ObjectId(exam_id)})
    if not exam:
        return jsonify({"message": "Exam not found"}), 404
        
    questions = exam['questions']
    score = 0
    
    # Calculate Score
    for i, q in enumerate(questions):
        # answers[i] is the option index selected by student
        if i < len(answers) and answers[i] == q['correctOption']:
            score += 1
            
    # Update Result
    exam_results_collection.update_one(
        {"examId": exam_id, "studentUsername": username},
        {"$set": {
            "status": "completed",
            "score": score,
            "total": len(questions),
            "submitted_at": datetime.now()
        }},
        upsert=True
    )
    
    return jsonify({"score": score, "total": len(questions)}), 200

@app.route('/api/exams/lock', methods=['POST'])
def lock_exam():
    # Called when tab switch is detected
    data = request.json
    exam_id = data.get('examId')
    username = data.get('username')
    
    exam_results_collection.update_one(
        {"examId": exam_id, "studentUsername": username},
        {"$set": {"status": "locked"}}
    )
    return jsonify({"message": "Exam locked due to malpractice"}), 200

@app.route('/api/exams/reset', methods=['POST'])
def reset_exam():
    # Teacher allows student to take exam again
    data = request.json
    exam_id = data.get('examId')
    username = data.get('studentUsername') # The student to reset
    
    exam_results_collection.delete_one({
        "examId": exam_id,
        "studentUsername": username
    })
    return jsonify({"message": "Exam reset for student"}), 200

@app.route('/api/exams/results/<exam_id>', methods=['GET'])
def get_exam_results(exam_id):
    results = list(exam_results_collection.find({"examId": exam_id}))
    for r in results:
        r['_id'] = str(r['_id'])
    return jsonify(results), 200


# --- Main execution ---
if __name__ == '__main__':
    print("🚀 Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)