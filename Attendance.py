import sqlite3
import qrcode
import json
import time
import requests
from datetime import datetime, date
import cv2
import numpy as np
from PIL import Image
import os
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import pandas as pd
import matplotlib.pyplot as plt

class AdvancedAttendanceSystem:
    def __init__(self, db_name='attendance.db'):
        self.db_name = db_name
        self.init_database()
        self.setup_directories()
        
    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs('qrcodes', exist_ok=True)
        os.makedirs('reports', exist_ok=True)
        os.makedirs('photos', exist_ok=True)
        
    def init_database(self):
        """Initialize SQLite database with advanced tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                section TEXT,
                photo_path TEXT,
                parent_email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attendance table with more details
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                date DATE NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Present',
                attendance_type TEXT DEFAULT 'QR',  # QR, Face, Manual
                location TEXT,
                device_id TEXT,
                FOREIGN KEY (student_id) REFERENCES students (student_id)
            )
        ''')
        
        # Classes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                class_id TEXT PRIMARY KEY,
                class_name TEXT NOT NULL,
                teacher_id TEXT,
                schedule TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def add_student(self, student_id, name, class_name, section='A', parent_email=None, photo_path=None):
        """Add a new student to the system"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students (student_id, name, class, section, parent_email, photo_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, name, class_name, section, parent_email, photo_path))
            
            conn.commit()
            print(f"Student {name} added successfully!")
            
            # Generate QR code for the student
            self.generate_student_qr(student_id)
            
        except sqlite3.IntegrityError:
            print(f"Student ID {student_id} already exists!")
        finally:
            conn.close()
    
    def generate_student_qr(self, student_id):
        """Generate QR code for student attendance"""
        qr_data = {
            'student_id': student_id,
            'timestamp': str(int(time.time())),
            'type': 'attendance'
        }
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        filename = f"qrcodes/{student_id}_qr.png"
        img.save(filename)
        print(f"QR code generated: {filename}")
        return filename
    
    def scan_qr_attendance(self):
        """Scan QR code for attendance using phone camera"""
        print("QR Scanner Started...")
        print("Point camera at student QR code")
        
        # For Termux, we can use termux-camera-photo
        qr_filename = f"temp_qr_{int(time.time())}.jpg"
        
        # Take photo using Termux camera
        os.system(f"termux-camera-photo -c 0 {qr_filename}")
        
        # Read and decode QR code
        try:
            img = cv2.imread(qr_filename)
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img)
            
            if data:
                qr_data = json.loads(data)
                student_id = qr_data['student_id']
                
                # Mark attendance
                self.mark_attendance(student_id, 'QR')
                print(f"Attendance marked for student ID: {student_id}")
            else:
                print("No QR code detected!")
                
        except Exception as e:
            print(f"Error scanning QR: {e}")
        finally:
            # Clean up temporary file
            if os.path.exists(qr_filename):
                os.remove(qr_filename)
    
    def mark_attendance(self, student_id, attendance_type='QR', status='Present'):
        """Mark attendance for a student"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        
        # Check if attendance already marked today
        cursor.execute('''
            SELECT id FROM attendance 
            WHERE student_id = ? AND date = ?
        ''', (student_id, today))
        
        if cursor.fetchone():
            print(f"Attendance already marked for student {student_id} today!")
            conn.close()
            return False
        
        # Get student details
        cursor.execute('SELECT name FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        
        if student:
            cursor.execute('''
                INSERT INTO attendance (student_id, date, status, attendance_type)
                VALUES (?, ?, ?, ?)
            ''', (student_id, today, status, attendance_type))
            
            conn.commit()
            print(f"Attendance marked for {student[0]} ({student_id})")
            
            # Send notification to parent
            self.send_parent_notification(student_id, status)
            
            conn.close()
            return True
        else:
            print(f"Student ID {student_id} not found!")
            conn.close()
            return False
    
    def send_parent_notification(self, student_id, status):
        """Send email notification to parent"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, parent_email FROM students WHERE student_id = ?
        ''', (student_id,))
        
        student = cursor.fetchone()
        conn.close()
        
        if student and student[1]:  # If parent email exists
            name, parent_email = student
            
            # Email configuration (you need to set up your SMTP details)
            try:
                # This is a template - you need to configure with actual SMTP
                message = MimeMultipart()
                message['From'] = 'attendance@school.com'
                message['To'] = parent_email
                message['Subject'] = f'Attendance Update - {name}'
                
                body = f"""
                Dear Parent,
                
                Your child {name} has been marked {status} today.
                Date: {date.today().strftime('%Y-%m-%d')}
                Time: {datetime.now().strftime('%H:%M:%S')}
                
                Thank you,
                School Attendance System
                """
                
                message.attach(MimeText(body, 'plain'))
                
                # You would add SMTP sending code here
                print(f"Would send email to {parent_email}: {status}")
                
            except Exception as e:
                print(f"Error sending email: {e}")
    
    def generate_daily_report(self, specific_date=None):
        """Generate daily attendance report"""
        if not specific_date:
            specific_date = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT s.class, s.section, 
                   COUNT(*) as total_students,
                   SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present,
                   SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id AND a.date = ?
            GROUP BY s.class, s.section
        '''
        
        df = pd.read_sql_query(query, conn, params=(specific_date,))
        conn.close()
        
        # Generate report file
        filename = f"reports/attendance_report_{specific_date}.csv"
        df.to_csv(filename, index=False)
        
        # Generate visual report
        self.generate_visual_report(df, specific_date)
        
        print(f"Report generated: {filename}")
        return df
    
    def generate_visual_report(self, df, date):
        """Generate visual charts for attendance"""
        if not df.empty:
            plt.figure(figsize=(12, 8))
            
            # Attendance by class
            plt.subplot(2, 2, 1)
            classes = [f"{row['class']}-{row['section']}" for _, row in df.iterrows()]
            present_counts = df['present']
            plt.bar(classes, present_counts)
            plt.title('Present Students by Class')
            plt.xticks(rotation=45)
            
            # Attendance percentage
            plt.subplot(2, 2, 2)
            attendance_percent = (df['present'] / df['total_students'] * 100).round(2)
            plt.pie(attendance_percent, labels=classes, autopct='%1.1f%%')
            plt.title('Attendance Percentage by Class')
            
            plt.tight_layout()
            plt.savefig(f'reports/attendance_chart_{date}.png')
            plt.close()
    
    def get_student_attendance(self, student_id):
        """Get attendance record for specific student"""
        conn = sqlite3.connect(self.db_name)
        
        query = '''
            SELECT date, status, attendance_type, timestamp
            FROM attendance 
            WHERE student_id = ?
            ORDER BY date DESC
            LIMIT 30
        '''
        
        df = pd.read_sql_query(query, conn, params=(student_id,))
        conn.close()
        
        if not df.empty:
            attendance_rate = (df['status'] == 'Present').mean() * 100
            print(f"Attendance Rate for {student_id}: {attendance_rate:.2f}%")
        
        return df
    
    def manual_attendance(self):
        """Manual attendance entry interface"""
        print("\n=== Manual Attendance Entry ===")
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Show classes
        cursor.execute("SELECT DISTINCT class, section FROM students ORDER BY class, section")
        classes = cursor.fetchall()
        
        for i, (class_name, section) in enumerate(classes, 1):
            print(f"{i}. {class_name}-{section}")
        
        try:
            choice = int(input("\nSelect class: ")) - 1
            selected_class, selected_section = classes[choice]
            
            # Get students in selected class
            cursor.execute('''
                SELECT student_id, name FROM students 
                WHERE class = ? AND section = ?
                ORDER BY name
            ''', (selected_class, selected_section))
            
            students = cursor.fetchall()
            
            print(f"\nMarking attendance for {selected_class}-{selected_section}")
            print("Enter 'P' for Present, 'A' for Absent, 'L' for Late")
            
            for student_id, name in students:
                status = input(f"{name} ({student_id}): ").upper()
                
                if status in ['P', 'A', 'L']:
                    status_map = {'P': 'Present', 'A': 'Absent', 'L': 'Late'}
                    self.mark_attendance(student_id, 'Manual', status_map[status])
                else:
                    print(f"Invalid input for {name}, skipping...")
                    
        except (ValueError, IndexError):
            print("Invalid selection!")
        finally:
            conn.close()
    
    def system_stats(self):
        """Display system statistics"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        # Today's attendance
        today = date.today().isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM attendance WHERE date = ?
        ''', (today,))
        today_attendance = cursor.fetchone()[0]
        
        # Classes count
        cursor.execute("SELECT COUNT(DISTINCT class) FROM students")
        total_classes = cursor.fetchone()[0]
        
        print(f"\n=== System Statistics ===")
        print(f"Total Students: {total_students}")
        print(f"Total Classes: {total_classes}")
        print(f"Today's Attendance Records: {today_attendance}")
        print(f"Date: {date.today().strftime('%Y-%m-%d')}")
        
        conn.close()

def main():
    system = AdvancedAttendanceSystem()
    
    while True:
        print("\n" + "="*50)
        print("       ADVANCED ATTENDANCE MONITORING SYSTEM")
        print("="*50)
        print("1. Add New Student")
        print("2. Scan QR Attendance")
        print("3. Manual Attendance Entry")
        print("4. Generate Daily Report")
        print("5. Student Attendance Record")
        print("6. System Statistics")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        try:
            if choice == '1':
                student_id = input("Student ID: ")
                name = input("Full Name: ")
                class_name = input("Class: ")
                section = input("Section (default A): ") or 'A'
                parent_email = input("Parent Email (optional): ") or None
                
                system.add_student(student_id, name, class_name, section, parent_email)
                
            elif choice == '2':
                system.scan_qr_attendance()
                
            elif choice == '3':
                system.manual_attendance()
                
            elif choice == '4':
                date_input = input("Enter date (YYYY-MM-DD) or press enter for today: ")
                system.generate_daily_report(date_input if date_input else None)
                
            elif choice == '5':
                student_id = input("Enter Student ID: ")
                system.get_student_attendance(student_id)
                
            elif choice == '6':
                system.system_stats()
                
            elif choice == '7':
                print("Thank you for using Attendance System!")
                break
                
            else:
                print("Invalid choice! Please try again.")
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check if running in Termux
    if os.path.exists('/data/data/com.termux/files/usr'):
        print("Termux environment detected!")
    else:
        print("Running in standard Python environment")
    
    main()
