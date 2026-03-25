from flask import Flask, render_template, redirect, request, url_for, session,jsonify, flash
from functools import wraps
from werkzeug.utils import secure_filename
import os
import math
import uuid
import face_recognition
from fpdf import FPDF
import base64
from flask import render_template_string, make_response
import numpy as np
import cv2
from datetime import datetime
import qrcode
import pdfkit


import pymysql
app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  
app.secret_key = "attendx_secret_key"
conn=pymysql.connect(host='localhost', user='root', password='', db='db_atten')
UPLOAD_FOLDER = 'static/student_img_upload/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route("/alogin_process", methods=["POST"])
def alogin_process():
    admin_email = request.form.get('admin_email')
    admin_pass = request.form.get('admin_pass')
    cursor = conn.cursor() 
    cursor.execute("SELECT * FROM admin_login WHERE admin_email=%s AND admin_pass=%s", (admin_email, admin_pass))
    admin = cursor.fetchone()
    if admin:
        session['admin_id'] = admin[0]
        session['admin_name'] = admin[1]
        session['admin_email'] = admin[2]
        session['Semester'] = admin[3]
        return redirect(url_for('dashboard'))
    return render_template("Admin/admin_login.html", error="Invalid email or password")

@app.route("/dashboard")
def dashboard():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor()
    query="SELECT COUNT(*) FROM student_data"
    cursor.execute(query)
    studata=cursor.fetchone()[0]
    query1 = "SELECT COUNT(*) FROM department_data"
    cursor.execute(query1)
    deptdata = cursor.fetchone()[0]
    query2 = "SELECT COUNT(*) FROM attendance"
    cursor.execute(query2)
    attenddata = cursor.fetchone()[0]
    query3 = "SELECT COUNT(*) FROM faculty_data"
    cursor.execute(query3)
    facultydata = cursor.fetchone()[0]
    return render_template("Admin/dashboard.html", studata=studata, deptdata=deptdata, attenddata=attenddata, facultydata=facultydata)

@app.route("/add_department")
def add_department():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/add_department.html")

@app.route("/insert_department", methods=["POST"])
def insert_department():
    department_name = request.form['Department_name'] 
    department_code = request.form['Department_code'] 
    hod_name = request.form['HOD_name']
    cursor = conn.cursor() 
    cursor.execute("INSERT INTO department_data (Department_name, Department_code, HOD_name) VALUES (%s, %s, %s)", (department_name, department_code, hod_name))
    conn.commit() 
    cursor.close() 
    return redirect(url_for('view_department'))

@app.route("/view_department")
def view_department():
    
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT *FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()
    
    return render_template("Admin/view_department.html", departments=departments)

@app.route("/delete_department/<int:Department_id>")
def delete_department(Department_id):
    cursor = conn.cursor()
    query = "DELETE FROM department_data WHERE Department_id=%s"
    val = (Department_id,)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_department'))

@app.route("/edit_department/<int:Department_id>")
def edit_department(Department_id):
    cursor = conn.cursor()
    query = "SELECT * FROM department_data WHERE Department_id=%s"
    cursor.execute(query, (Department_id,))
    department = cursor.fetchone()
    cursor.close()
    return render_template("Admin/edit_department.html", department=department)

@app.route("/edit_department_process/<int:Department_id>", methods=["POST"])
def edit_department_process(Department_id):
    department_name = request.form['Department_name']
    department_code = request.form['Department_code']
    hod_name = request.form['HOD_name']
    cursor = conn.cursor()
    query = "UPDATE department_data SET Department_name=%s, Department_code=%s, HOD_name=%s WHERE Department_id=%s"
    val = (department_name, department_code, hod_name, Department_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_department'))

@app.route("/analytics")
def analytics():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/analytics.html")

@app.route("/")
def login():
    return render_template("Admin/admin_login.html")

@app.route("/add_user")
def add_user():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()


    query = "SELECT *FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()

    return render_template("Admin/add_user.html",departments=departments)



@app.route("/studentprocess", methods=["POST"])
def studentprocess():

    if 'admin_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:

        Student_name = request.form['student_name']
        Division = request.form['Division']
        Enrollment_no = request.form['Enrollment_no']
        Department_id = request.form['Department_id']
        Semester = request.form['Semester']
        Email = request.form['Email']
        password = request.form['password']
        contact = request.form['contact']

        filename = None

        if 'captured_image' in request.files:

            file = request.files['captured_image']

            if file and file.filename != "":

                unique_id = str(uuid.uuid4())
                extension = os.path.splitext(file.filename)[1].lower()

                allowed_extensions = ['.png', '.jpg', '.jpeg']

                if extension not in allowed_extensions:
                    return jsonify({"success": False, "message": "Invalid image format"})

                filename = unique_id + extension

                filepath = os.path.join(UPLOAD_FOLDER, filename)

                
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)

                file.save(filepath)

                # --- NEW FACE VALIDATION LOGIC ---
                try:
                    loaded_img = face_recognition.load_image_file(filepath)
                    encodings = face_recognition.face_encodings(loaded_img)

                    if len(encodings) == 0:
                        os.remove(filepath) # Clean up invalid image
                        return jsonify({"success": False, "message": "No face detected in the webcam capture! Please try again."})
                    
                    if len(encodings) > 1:
                        os.remove(filepath)
                        return jsonify({"success": False, "message": "Multiple faces detected! Please ensure only the student is in the frame."})
                        
                except Exception as eval_e:
                    print("Face validation error:", eval_e)
                    return jsonify({"success": False, "message": "Could not validate face image."})
                # ---------------------------------

        cursor = conn.cursor()

        query = """
        INSERT INTO student_data
        (Student_name, Division, Enrollment_no, Department_id,
        Semester, Email, password, contact, img_of_student)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        

        values = (
            Student_name,
            Division,
            Enrollment_no,
            Department_id,
            Semester,
            Email,
            password,
            contact,
            filename
        )

        cursor.execute(query, values)
        conn.commit()

        cursor.close()

        return jsonify({"success": True})

    except Exception as e:

        print("Error:", e)

        return jsonify({
            "success": False,
            "message": "Student insertion failed"
        })

@app.route("/view_user")
def view_user():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT * FROM student_data join department_data on student_data.Department_id=department_data.Department_id"
    cursor.execute(query,)
    students = cursor.fetchall()
    return render_template("Admin/view_user.html", students=students)

@app.route("/delete_user/<int:Student_id>")
def delete_user(Student_id):
    cursor = conn.cursor()
    query = "DELETE FROM student_data WHERE Student_id=%s"
    val = (Student_id,) 
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_user'))

@app.route("/edit_user/<int:Student_id>")
def edit_user(Student_id):
    cursor = conn.cursor()

    query = "SELECT * FROM student_data WHERE Student_id=%s"
    cursor.execute(query, (Student_id,))
    student = cursor.fetchone()

    query = "SELECT * FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()

    cursor.close()
    return render_template(
        "Admin/edit_user.html",
        student=student,
        departments=departments
    )

@app.route("/edit_user_process/<int:Student_id>", methods=["POST"])
def edit_user_process(Student_id):
    student_name = request.form['student_name']
    Division = request.form['Division']
    Enrollment_no = request.form['Enrollment_no']
    Department_id = request.form['Department_id']
    Semester = request.form['Semester']
    Email = request.form['Email']
    password = request.form['password']
    contact = request.form['contact']

    cursor = conn.cursor()
    query = "UPDATE student_data SET Student_name=%s, Division=%s, Enrollment_no=%s, Department_id=%s, Semester=%s, Email=%s, Password=%s, Contact=%s WHERE Student_id=%s"
    val = (student_name, Division, Enrollment_no, Department_id, Semester, Email, password, contact, Student_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_user',))


@app.route("/add_faculty")
def add_faculty():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT *FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()
    cursor.close()
    return render_template("Admin/add_faculty.html",departments=departments)

@app.route("/insert_faculty", methods=["POST"])
def insert_faculty():
    Faculty_name = request.form['Faculty_name']
    Faculty_email = request.form['Faculty_email']
    Department_id = request.form['Department_id']
    contact = request.form['contact']
    Password = request.form['Password']
    cursor = conn.cursor()
    
    select_query = "SELECT * FROM faculty_data WHERE Faculty_email=%s"
    cursor.execute(select_query, (Faculty_email,))
    existing_faculty = cursor.fetchone()
    if existing_faculty:
        cursor.close()
        return render_template("Admin/add_faculty.html", error="A faculty member with this email already exists.")
    
    query = "INSERT INTO faculty_data(Faculty_name, Faculty_email, Department_id, contact, Password) VALUES (%s, %s, %s, %s, %s)"
    cursor.execute(query, (Faculty_name, Faculty_email, Department_id, contact, Password))
    conn.commit()
    cursor.close()
    return redirect(url_for('view_faculty'))

@app.route("/view_faculty")
def view_faculty():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT f.Faculty_id, f.Faculty_name, f.Faculty_email, f.Department_id, f.Contact, d.Department_name FROM faculty_data f JOIN department_data d on f.Department_id=d.Department_id"
    cursor.execute(query)
    faculty_members = cursor.fetchall()
    return render_template("Admin/view_faculty.html", faculty_members=faculty_members)

@app.route("/delete_faculty/<int:Faculty_id>")
def delete_faculty(Faculty_id):
    cursor = conn.cursor()
    query = "DELETE FROM faculty_data WHERE Faculty_id=%s"
    val = (Faculty_id,)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_faculty'))

@app.route("/edit_faculty/<int:Faculty_id>")
def edit_faculty(Faculty_id):
    cursor = conn.cursor()
    query = "SELECT * FROM faculty_data WHERE Faculty_id=%s"
    cursor.execute(query, (Faculty_id,))
    faculty = cursor.fetchone()

    query = "SELECT * FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()

    cursor.close()
    return render_template(
        "Admin/edit_faculty.html",
        faculty=faculty,
        departments=departments
    )

@app.route("/edit_faculty_process/<int:Faculty_id>", methods=["POST"])
def edit_faculty_process(Faculty_id):
    Faculty_name = request.form['Faculty_name']
    Faculty_email = request.form['Faculty_email']
    Department_id = request.form['Department_id']
    contact = request.form['contact']
    Password = request.form['Password']

    cursor = conn.cursor()
    query = "UPDATE faculty_data SET Faculty_name=%s, Faculty_email=%s, Department_id=%s, contact=%s, Password=%s WHERE Faculty_id=%s"
    val = (Faculty_name, Faculty_email, Department_id, contact, Password, Faculty_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_faculty'))

@app.route("/add_class")
def add_class():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT *FROM faculty_data"
    cursor.execute(query)
    faculty_members = cursor.fetchall()
    
    
    query = "SELECT *FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()
    cursor.close()

    return render_template("Admin/add_class.html",faculty_members=faculty_members,departments=departments)

@app.route("/insert_class", methods=["POST"])
def insert_class():
    class_name = request.form['class_name']
    Faculty_id = request.form['Faculty_id']
    Department_id = request.form['Department_id']
    semester = request.form['semester']
    room_no = request.form['room_no']
    latitude = request.form['latitude']
    longitude = request.form['longitude']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    cursor = conn.cursor()
    query = "INSERT INTO class_data(class_name, Faculty_id, Department_id, semester, room_no, latitude, longitude,date, start_time, end_time) VALUES (%s, %s, %s, %s, %s,%s,%s, %s,%s,%s)"
    cursor.execute(query, (class_name, Faculty_id, Department_id, semester, room_no, latitude, longitude, date, start_time, end_time))
    conn.commit()
    cursor.close()
    return redirect(url_for('view_class'))

@app.route("/view_class")
def view_class():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    cursor = conn.cursor()
    query = "SELECT * from class_data Join faculty_data on class_data.Faculty_id=faculty_data.Faculty_id Join department_data on class_data.Department_id=department_data.Department_id"
    cursor.execute(query)
    classes = cursor.fetchall()
    cursor.close()
    return render_template("Admin/view_class.html", classes=classes)

@app.route("/delete_class/<int:class_id>")
def delete_class(class_id):
    cursor = conn.cursor()
    query = "DELETE FROM class_data WHERE class_id=%s"
    val = (class_id,)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_class'))

@app.route("/edit_class/<int:class_id>")
def edit_class(class_id):
    cursor = conn.cursor()
    query = "SELECT * FROM class_data WHERE Class_id=%s"
    cursor.execute(query, (class_id,))
    class_data = cursor.fetchone()

    query = "SELECT * FROM faculty_data"
    cursor.execute(query)
    faculty_members = cursor.fetchall()

    query = "SELECT * FROM department_data"
    cursor.execute(query)
    departments = cursor.fetchall()

    cursor.close()
    return render_template(
        "Admin/edit_class.html",
        class_data = class_data,
        faculty_members=faculty_members,
        departments=departments
    )

@app.route("/edit_class_process/<int:class_id>", methods=["POST"])
def edit_class_process(class_id):
    class_name = request.form['class_name']
    Faculty_id = request.form['Faculty_id']
    Department_id = request.form['Department_id']
    semester = request.form['semester']
    room_no = request.form['room_no']
    latitude = request.form['latitude']
    longitude = request.form['longitude']
    date = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']

    cursor = conn.cursor()
    query = "UPDATE class_data SET class_name=%s, Faculty_id=%s, Department_id=%s, semester=%s, room_no=%s, latitude=%s, longitude=%s, date=%s, start_time=%s, end_time=%s WHERE class_id=%s"
    val = (class_name, Faculty_id, Department_id, semester, room_no, latitude, longitude,date, start_time, end_time,class_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('view_class'))

@app.route("/export_pdf/<int:Student_id>")
def export_pdf(Student_id):
    cursor = conn.cursor()

    query = """
    SELECT 
    s.Student_name,
    s.Enrollment_no,
    d.Department_name,
    s.Semester,
    a.date,
    a.status
    FROM attendance a
    JOIN student_data s ON a.Student_id = s.Student_id
    JOIN department_data d ON s.Department_id = d.Department_id
    WHERE a.Student_id = %s
    """

    cursor.execute(query, (Student_id,))
    data = cursor.fetchall()
    cursor.close()

    rendered = render_template("Admin/attendance_pdf.html", data=data)

    pdf = pdfkit.from_string(rendered, False, configuration=config)

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=attendance.pdf'

    return response

@app.route("/report")
def report():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    cursor = conn.cursor()

    query = "SELECT a.Student_id,Student_name,Enrollment_no,Semester,b.Department_name FROM student_data as a,department_data as b WHERE a.Department_id = b.Department_id;"
    
    
    cursor.execute(query)
    student = cursor.fetchall()
    conn.commit()
    cursor.close()
    return render_template("Admin/report.html", student=student)

@app.route("/viewattendance/<int:Student_id>")
def view_attendance(Student_id):
    cursor = conn.cursor()

    query = """
    SELECT 
    s.Student_name,
    s.Enrollment_no,
    d.Department_name,
    s.Semester,
    a.date,
    a.status
    FROM attendance a
    JOIN student_data s ON a.Student_id = s.Student_id
    JOIN department_data d ON s.Department_id = d.Department_id
    WHERE a.Student_id = %s
    """

    cursor.execute(query, (Student_id,))
    data = cursor.fetchall()

    cursor.close()

    return render_template("Admin/view_attendance.html", data=data)

@app.route("/attendance_rule")
def attendance():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/attendance_rule.html")

@app.route("/allowed-time_window")
def settings():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/allowed_time_window.html")

@app.route("/gps_range")
def gps_range():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/gps_range.html")

@app.route("/camera_setting")
def camera_setting():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/camera_setting.html")

@app.route("/backup_database")
def backup_database():

    if 'admin_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("Admin/backup_database.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/faculty_login_process", methods=["POST"])
def faculty_login_process():
    Faculty_email = request.form['Faculty_email']
    Password = request.form['Password']
    cursor = conn.cursor()
    query = '''SELECT f.Faculty_id, f.Faculty_name, f.Faculty_email, f.Department_id, f.Contact, d.Department_name FROM faculty_data f 
    JOIN department_data d on f.Department_id=d.Department_id WHERE Faculty_email=%s AND Password=%s'''
    cursor.execute(query, (Faculty_email, Password))
    faculty = cursor.fetchone()
    if faculty:
        session['faculty_id'] = faculty[0]
        session['Faculty_name'] = faculty[1]
        session['Faculty_email'] = faculty[2]
        session['Department_id'] = faculty[3]
        session['contact'] = faculty[4]
        session['Department_name'] = faculty[5]
        return redirect(url_for('faculty_dashboard'))
    else:
        flash("Invalid Email or Password")
        return redirect(url_for("faculty_login"))
    
@app.route("/faculty_login")
def faculty_login():
    return render_template("Faculty/faculty_login.html")

@app.route("/faculty_dashboard")
def faculty_dashboard():
    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))

    faculty_id = session['faculty_id']
    department_id = session['Department_id']

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT COUNT(*) AS total FROM class_data WHERE Faculty_id=%s",
        (faculty_id,)
    )
    classdata = cursor.fetchone()['total']

    cursor.execute(
        "SELECT COUNT(*) AS total FROM student_data WHERE Department_id=%s",
        (department_id,)
    )
    total_students = cursor.fetchone()['total']

    cursor.execute("""
        SELECT *
        FROM class_data
        WHERE Faculty_id=%s AND date = CURDATE()
        ORDER BY start_time
    """, (faculty_id,))
    today_classes = cursor.fetchall()

    today_classes_count = len(today_classes)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE date = CURDATE()
    """)
    today_attendance = cursor.fetchone()['total']

    pending_classes = today_classes_count - today_attendance
    if pending_classes < 0:
        pending_classes = 0

    cursor.execute("""
        SELECT *
        FROM class_data
        WHERE Faculty_id=%s AND date = CURDATE()
        ORDER BY start_time
        LIMIT 1
    """, (faculty_id,))
    next_class = cursor.fetchone()

    cursor.close()

    return render_template(
        "Faculty/faculty_dashboard.html",
        classdata=classdata,
        total_students=total_students,
        today_attendance=today_attendance,
        pending_classes=pending_classes,
        today_classes=today_classes,
        next_class=next_class
    )

@app.route("/faculty_layout")
def faculty_layout():
    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    
    return render_template("Faculty/layout.html")

@app.route("/myclasses")
def myclasses():

    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    faculty_id = session['faculty_id']
    query = "SELECT class_data.*, faculty_data.Faculty_name, department_data.Department_name FROM class_data " \
    "JOIN faculty_data ON class_data.Faculty_id = faculty_data.Faculty_id " \
    "JOIN department_data ON class_data.Department_id = department_data.Department_id WHERE class_data.Faculty_id = %s"
    cursor = conn.cursor()
    cursor.execute(query, (faculty_id,))
    classes = cursor.fetchall()
    cursor.close()
    
    return render_template("Faculty/myclasses.html", classes=classes)

@app.route("/start_attendance")
def show_attendance():

    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    
    return render_template("Faculty/start_attendance.html")

@app.route("/faculty_student_report")
def faculty_student_report():

    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    return render_template("Faculty/faculty_student_report.html")

@app.route("/faculty_profile")
def faculty_profile():
    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    
    return render_template("Faculty/faculty_profile.html")

@app.route("/faculty_edit_profile")
def faculty_edit_profile():
    if 'faculty_id' not in session:
        return redirect(url_for('faculty_login'))
    
    cursor = conn.cursor()
    faculty_id = session['faculty_id']

    cursor.execute("""
        SELECT Faculty_id, Faculty_name, Faculty_email, 
            Password, Department_id, contact
        FROM faculty_data
        WHERE Faculty_id=%s
    """, (faculty_id,))

    faculty = cursor.fetchall()

    cursor.execute("SELECT * FROM department_data")
    departments = cursor.fetchall()

    cursor.close()

    return render_template(
        "Faculty/faculty_edit_profile.html",
        faculty=faculty,
        departments=departments
    )

@app.route("/edit_faculty_profile_process/<int:Faculty_id>", methods=["POST"])
def edit_faculty_profile_process(Faculty_id):
    Faculty_name = request.form['Faculty_name']
    Faculty_email = request.form['Faculty_email']
    Department_id = request.form['Department_id']
    contact = request.form['contact']
    Password = request.form['Password']

    cursor = conn.cursor()
    query = "UPDATE faculty_data SET Faculty_name=%s, Faculty_email=%s, Department_id=%s, contact=%s, Password=%s WHERE Faculty_id=%s"
    val = (Faculty_name, Faculty_email, Department_id, contact, Password, Faculty_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('faculty_profile'))

@app.route("/faculty_logout")
def faculty_logout():
    session.clear()
    return redirect(url_for('faculty_login'))

@app.route("/student_login_process", methods=["POST"])
def student_login_process():
    Enrollment_no = request.form['Enrollment_no']
    password = request.form['password']

    cursor = conn.cursor()

    query = """
        SELECT s.Student_id, s.Student_name, s.Enrollment_no,
            s.Department_id, s.Email, s.contact,
            d.Department_name
        FROM student_data s
        JOIN department_data d
        ON s.Department_id = d.Department_id
        WHERE s.Enrollment_no=%s AND s.password=%s
    """

    cursor.execute(query, (Enrollment_no, password))
    student = cursor.fetchone()
    conn.commit()
    cursor.close()

    if student:
        session['Student_id'] = student[0]
        session['Student_name'] = student[1]
        session['Enrollment_no'] = student[2]
        session['Department_id'] = student[3]
        session['Email'] = student[4]
        session['contact'] = student[5]
        session['Department_name'] = student[6]

        return redirect(url_for('student_dashboard'))
    else:
        flash("Invalid Enrollment No or Password")
        return redirect(url_for('student_login'))



@app.route("/student_login")
def student_login():

    return render_template("Student/student_login.html")

@app.route("/student_dashboard")
def student_dashboard():

    if 'Student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['Student_id']
    department_id = session['Department_id']

    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT COUNT(*) as total FROM class_data WHERE Department_id=%s",
        (department_id,))
    total_classes = cursor.fetchone()['total']

    cursor.execute("""
    SELECT *
    FROM class_data
    WHERE Department_id=%s AND date=CURDATE()
    """,(department_id,))
    today_classes = cursor.fetchall()

    today_classes_count = len(today_classes)

    cursor.execute("""
    SELECT COUNT(*) as total
    FROM attendance
    WHERE Student_id=%s
    """,(student_id,))
    total_attendance = cursor.fetchone()['total']

    attendance_percentage = 0
    if total_classes > 0:
        attendance_percentage = round((total_attendance/total_classes)*100)

    cursor.execute("""
    SELECT *
    FROM class_data
    WHERE Department_id=%s AND date=CURDATE()
    ORDER BY start_time
    LIMIT 1
    """,(department_id,))
    next_class = cursor.fetchone()

    cursor.close()

    return render_template(
        "Student/student_dashboard.html",
        total_classes=total_classes,
        today_classes=today_classes,
        today_classes_count=today_classes_count,
        attendance_percentage=attendance_percentage,
        next_class=next_class
    )

@app.route("/classes")

def classes():

    if 'Student_id' not in session:
        return redirect(url_for('student_login'))
    student_id = session['Student_id']
    cursor = conn.cursor()


    cursor.execute(
        "SELECT Department_id FROM student_data WHERE Student_id=%s",
        (student_id,)

    )
    student = cursor.fetchone()
    if not student:
        cursor.close()
        return "Student not found"
    Department_id = student[0]
    cursor.execute(
        """SELECT c.class_id, c.class_name, f.faculty_name,d.department_name, c.room_no, c.date, c.start_time, c.end_time, c.latitude, c.longitude
        FROM class_data c
        JOIN faculty_data f ON c.faculty_id = f.faculty_id
        JOIN Department_data d ON c.Department_id=d.Department_id 
        WHERE c.Department_id=%s""",
        (Department_id,)
    )
    classes = cursor.fetchall()
    cursor.close()
    return render_template("Student/classes.html", classes = classes)

@app.route("/student_profile")
def student_profile():
    
    if 'Student_id' not in session:
        return redirect(url_for('student_login'))
    cursor = conn.cursor()
    student_id = session['Student_id']
    query="select * from student_data where Student_id=%s"
    cursor.execute(query, (student_id,))
    student = cursor.fetchall()
    cursor.close()
    
    return render_template("Student/student_profile.html", student=student)

@app.route("/student_edit_profile/<int:Student_id>")
def student_edit_profile(Student_id):
    
    if 'Student_id' not in session:
        return redirect(url_for('student_login'))
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Student_id, Student_name, Email, 
            password, Department_id, contact
        FROM student_data
        WHERE Student_id=%s
    """, (Student_id,))

    student = cursor.fetchall()

    cursor.execute("SELECT * FROM department_data")
    departments = cursor.fetchall()

    cursor.close()

    return render_template("Student/edit_profile.html",
                        departments=departments,
                        student=student)

@app.route("/student_edit_profile_process", methods=['POST'] )
def student_edit_profile_process():
    Student_id = request.form['Student_id']

    Student_name = request.form['Student_name']
    Email = request.form['Email']
    Department_id = request.form['Department_id']
    contact = request.form['contact']
    password = request.form['password']

    cursor = conn.cursor()
    query = "UPDATE student_data SET Student_name=%s, Email=%s, Department_id=%s, contact=%s, password=%s WHERE Student_id=%s"
    val = (Student_name, Email, Department_id, contact, password, Student_id)
    cursor.execute(query, val)
    conn.commit()
    cursor.close()
    return redirect(url_for('student_profile'))

@app.route("/student_attendance_report")
def student_attendance_report():

    if 'Student_id' not in session:
        return redirect(url_for('student_login'))
    
    return render_template("Student/student_attendance_report.html")

@app.route("/mark_attendance/<int:class_id>")
def mark_attendance(class_id):

    if 'Student_id' not in session:
        return redirect(url_for('student_login'))

    return render_template(
        "Student/mark_attendance.html",
        class_id=class_id
    )

def calculate_distance(lat1, lon1, lat2, lon2):

    R = 6371000

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    distance = R * c

    return distance

@app.route("/mark_attendanceprocess", methods=["POST"])
def mark_attendanceprocess():

    class_id = request.form.get('class_id')
    student_id = session.get('Student_id')
    if not student_id:
        return redirect(url_for('student_login'))
    if not class_id:
        print("ERROR: class_id is missing from form")
        print("Full form data:", request.form)
        return "Invalid class ID"


    image_data = request.form['image_data']
    class_id = int(class_id)
    # student_lat = request.form['latitude']
    # student_lon = request.form['longitude']
    # print("Received class_id:", class_id)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    # print("Class ID:", class_id)

    # cursor.execute("""
    # SELECT latitude, longitude
    # FROM class_data
    # WHERE class_id=%s
    # """,(class_id,))

    # class_location = cursor.fetchone()
    # print("Class location result:", class_location)

    # if not class_location:
    #     return "Class location not found"

    # class_lat = class_location['latitude']
    # class_lon = class_location['longitude']


    # distance = calculate_distance(student_lat, student_lon, class_lat, class_lon)
    # print(request.form)
    # if distance > 300:
    #     return "You are not in classroom location"

    image_data = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    unknown_encodings = face_recognition.face_encodings(rgb_frame)

    if len(unknown_encodings) == 0:
        flash("No face detected in the image. Please try again.", "danger")
        return redirect(url_for('mark_attendance', class_id=class_id))

    unknown_encoding = unknown_encodings[0]
    if len(unknown_encodings) > 1:
        flash("Multiple faces detected! Please ensure only you are in the frame.", "danger")
        return redirect(url_for('mark_attendance', class_id=class_id))

    cursor.execute(
        "SELECT Student_id, img_of_student FROM student_data WHERE Student_id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    if not student:
        flash("Student record not found in database.", "danger")
        return redirect(url_for('student_dashboard'))

    img_filename = student['img_of_student']
    img_path = os.path.join("static/student_img_upload", img_filename)

    if not os.path.exists(img_path):
        flash("Your registration image is missing. Please contact admin.", "danger")
        return redirect(url_for('student_dashboard'))

    known_image = face_recognition.load_image_file(img_path)
    known_encodings = face_recognition.face_encodings(known_image)

    if len(known_encodings) == 0:
        flash("No face was found in your stored registration image.", "danger")
        return redirect(url_for('student_dashboard'))

    known_encoding = known_encodings[0]


    distance = face_recognition.face_distance([known_encoding], unknown_encoding)

    # Relaxed tolerance from 0.5 to 0.55 to reduce false rejections due to lighting
    if distance[0] < 0.55:

        today = datetime.now().date()

        cursor.execute("""
        SELECT *
        FROM attendance
        WHERE Student_id=%s AND date=%s AND class_id=%s
        """, (student['Student_id'], today, class_id))

        already = cursor.fetchone()

        if already:
            flash("Attendance has already been marked for this class today.", "warning")
            return redirect(url_for('student_dashboard'))

        cursor.execute("""
        INSERT INTO attendance (Student_id, class_id, date, status)
        VALUES (%s, %s, %s, %s)
        """, (student['Student_id'], class_id, today, "Present"))
        conn.commit()

        flash("Attendance Marked Successfully!", "success")
        return redirect(url_for('student_dashboard'))
    
    flash("Face does not match the registered user. Attendance denied.", "danger")
    return redirect(url_for('mark_attendance', class_id=class_id))

@app.route("/student_logout")
def student_logout():
    session.clear()
    return redirect(url_for('student_login'))

if __name__ == '__main__':
    app.run(debug=True)