import sqlite3
import hashlib
import datetime
from typing import Optional
import streamlit as st

class TaskDB:
    def __init__(self, db_path="task_manager.db"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Create a database connection"""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return None

    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        if conn is not None:
            try:
                c = conn.cursor()
                
                # Create users table
                c.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY,
                 email TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                
                # Create tasks table
                c.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        task TEXT NOT NULL,
                        customer TEXT,
                        due_date TEXT,
                        priority TEXT,
                        status TEXT DEFAULT 'active',
                        completion_date TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
                
                conn.commit()
            except Exception as e:
                st.error(f"Database initialization error: {e}")
            finally:
                conn.close()

    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, email: str, password: str) -> bool:
        """Register a new user"""
        try:
            print("Registering...")
            conn = self.get_connection()
            print("Conneted...")
            if conn is not None:
                c = conn.cursor()
                hashed_password = self.hash_password(password)
                print("Email :",email)
                print("Password :",hashed_password)
                c.execute(
                    "INSERT INTO users (email, password) VALUES (?, ?)",
                    (email, hashed_password)
                )
                print("committing...")
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print("Exception..")
            return False
        finally:
            if conn:
                conn.close()
        return False

    def verify_user(self, email: str, password: str) -> Optional[dict]:
        """Verify user credentials"""
        try:
            conn = self.get_connection()
            print("Login ...")
            if conn is not None:
                c = conn.cursor()
                hashed_password = self.hash_password(password)
                print("Email :",email)
                print("Password :",hashed_password)
                c.execute(
                    "SELECT id, email FROM users WHERE email=? AND password=?",
                    (email, hashed_password)
                )
                user = c.fetchone()
                print("User :",user)
                if user:
                    return {
                        "id": user[0],
                        "email": user[1]
                    }
        finally:
            if conn:
                conn.close()
        return None

    def save_task(self, user_id: int, task_data: dict) -> bool:
        """Save a new task"""
        conn = self.get_connection()
        if conn is not None:
            try:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO tasks (user_id, task, customer, due_date, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    task_data['task'],
                    task_data['customer'],
                    task_data['due_date'],
                    task_data['priority']
                ))
                conn.commit()
                return True
            except Exception as e:
                st.error(f"Error saving task: {e}")
                return False
            finally:
                conn.close()
        return False

    def get_tasks(self, user_id: int, status: str = 'active') -> list:
        """Get user's tasks"""
        conn = self.get_connection()
        if conn is not None:
            try:
                c = conn.cursor()
                c.execute("""
                    SELECT id, task, customer, due_date, priority, completion_date
                    FROM tasks 
                    WHERE user_id=? AND status=?
                    ORDER BY due_date
                """, (user_id, status))
                tasks = c.fetchall()
                return [{
                    "id": t[0],
                    "task": t[1],
                    "customer": t[2],
                    "due_date": t[3],
                    "priority": t[4],
                    "completion_date": t[5]
                } for t in tasks]
            finally:
                conn.close()
        return []

    def complete_task(self, user_id: int, task_id: int) -> bool:
        """Mark a task as completed"""
        conn = self.get_connection()
        if conn is not None:
            try:
                c = conn.cursor()
                completion_date = datetime.datetime.now().strftime('%d-%m-%Y %H:%M')
                c.execute("""
                    UPDATE tasks 
                    SET status='completed', completion_date=?
                    WHERE id=? AND user_id=?
                """, (completion_date, task_id, user_id))
                conn.commit()
                return True
            except Exception as e:
                st.error(f"Error completing task: {e}")
                return False
            finally:
                conn.close()
        return False

    def delete_task(self, user_id: int, task_id: int) -> bool:
        """Delete a task"""
        conn = self.get_connection()
        if conn is not None:
            try:
                c = conn.cursor()
                c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, user_id))
                conn.commit()
                return True
            except Exception as e:
                st.error(f"Error deleting task: {e}")
                return False
            finally:
                conn.close()
        return False