from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import hashlib
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure random key

# Function to connect to MySQL database
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="$password",  # Change this to your MySQL password
        database="projectdb"
    )

# Function to hash passwords using SHA-256
def hash_password(password):
    hashed = hashlib.sha256(password.encode()).digest()
    return base64.b64encode(hashed).decode()

# Route to display the signup page
@app.route("/")
@app.route("/signup")
def signup():
    return render_template("signup.html")

# Route to handle user registration
@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        flash("Passwords do not match!", "error")
        return redirect(url_for('register'))  # Redirect back to the register page

    email = request.form["email"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    phone = request.form["phone"]
    
    hashed_password = hash_password(password)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO user (username, password, firstName, lastName, email, phone)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, hashed_password, first_name, last_name, email, phone))
        conn.commit()
        flash("User registered successfully!", "success")
        return redirect(url_for("login"))
    except mysql.connector.Error:
        flash("Error: Username, email, or phone already taken.", "danger")
        return redirect(url_for("signup"))
    finally:
        cursor.close()
        conn.close()

# Route to display the login page
@app.route("/login")
def login():
    return render_template("login.html")

# Route to handle user login
@app.route("/login_user", methods=["POST"])
def login_user():
    username = request.form["username"]
    password = request.form["password"]
    
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM user WHERE username = %s", (username,))
    result = cursor.fetchone()
    
    if result and result[0] == hash_password(password):
        session["username"] = username
        flash("Login successful! Welcome back.", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

# Route for user dashboard (after login)
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        return f"Welcome, {session['username']}! <br><a href='/logout'>Logout</a>"
    else:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

### code for rental unit, need to make a page in html before implementing this
###   
###   # Get the current user ID from the session or app context
###   user_id = 1  # example user
###   
###   # Query to count how many listings they posted today
###   cursor.execute("""
###       SELECT COUNT(*) FROM rental_unit
###       WHERE user_id = %s AND DATE(posted_at) = CURDATE()
###   """, (user_id,))
###   (post_count,) = cursor.fetchone()
###   
###   if post_count >= 2:
###       flash("You can only post 2 rental units per day.", "danger")
###       return redirect(url_for("post_rental"))
###   
###   # Otherwise, insert new rental
###   cursor.execute("""
###       INSERT INTO rental_unit (user_id, title, description, features, price)
###       VALUES (%s, %s, %s, %s, %s)
###   """, (user_id, title, description, features, price))
###   conn.commit()
###   

# Route to handle user logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
