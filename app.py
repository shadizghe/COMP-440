from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import hashlib
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"  

def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="$password",  
        database="projectdb"
    )

def hash_password(password):
    hashed = hashlib.sha256(password.encode()).digest()
    return base64.b64encode(hashed).decode()

@app.route("/")
@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = request.form["password"]
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        flash("Passwords do not match!", "error")
        return redirect(url_for('signup'))

    email = request.form["email"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    phone = request.form["phone"]
    
    hashed_password = hash_password(password)
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
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
    cursor.close()
    conn.close()
    
    if result and result[0] == hash_password(password):
        session["username"] = username
        flash("Login successful! Welcome back.", "success")
        return redirect(url_for("landing"))
    else:
        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

# Route for user landing page (after login)
@app.route("/landing")
def landing():
    if "username" in session:
        return render_template("landing.html", username=session["username"])
    else:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

# Route for creating a listing
@app.route("/create_listing")
def create_listing():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    listings_left = 2
    return render_template("create_listing.html", listings_left=listings_left)

# Route to handle listing submission
@app.route("/submit_listing", methods=["POST"])
def submit_listing():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    title = request.form["title"]
    details = request.form.get("description")
    features = request.form["features"]
    price = request.form["price"]
    username = session["username"]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        cursor.execute(
            """
            INSERT INTO rental_unit (user_id, title, details, features, price)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, title, details, features, price))
        conn.commit()
        flash("Listing created successfully!", "success")
    else:
        flash("User not found.", "danger")
    cursor.close()
    conn.close()
    return redirect(url_for("landing"))

# Route for searching for listings
@app.route("/search_listing")
def search_listing():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    feature = request.args.get("feature")
    listings = []

    if feature:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, title, details AS description, features, price, posted_at
            FROM rental_unit
            WHERE features LIKE %s
            """, (f"%{feature}%",))
        listings = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template("search_listing.html", listings=listings)

# Analytics Route 1: Most active posters on specific date
@app.route("/analytics/most_active_posters")
def most_active_posters():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    
    target_date = "2025-04-15"  # This could be made parameterizable
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT u.username, COUNT(ru.id) as unit_count
        FROM user u
        JOIN rental_unit ru ON u.id = ru.user_id
        WHERE DATE(ru.posted_at) = %s
        GROUP BY u.id, u.username
        HAVING COUNT(ru.id) = (
            SELECT COUNT(ru2.id) as max_count
            FROM rental_unit ru2
            WHERE DATE(ru2.posted_at) = %s
            GROUP BY ru2.user_id
            ORDER BY max_count DESC
            LIMIT 1
        )
    """
    cursor.execute(query, (target_date, target_date))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("analytics_results.html", 
                         title="Most Active Posters on 4/15/2025",
                         results=results)

# Analytics Route 2: Users who only gave poor reviews
@app.route("/analytics/poor_reviewers")
def poor_reviewers():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT DISTINCT u.username
        FROM user u
        JOIN review r ON u.id = r.reviewer_id
        WHERE u.id NOT IN (
            SELECT DISTINCT reviewer_id 
            FROM review 
            WHERE rating != 'poor'
        )
    """
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("analytics_results.html",
                         title="Users Who Only Gave Poor Reviews",
                         results=results)

# Analytics Route 3: Users whose listings never got poor reviews
@app.route("/analytics/no_poor_reviews")
def no_poor_reviews():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT DISTINCT u.username
        FROM user u
        JOIN rental_unit ru ON u.id = ru.user_id
        WHERE NOT EXISTS (
            SELECT 1 
            FROM review r 
            WHERE r.rental_unit_id = ru.id 
            AND r.rating = 'poor'
        )
        AND u.id IN (
            SELECT DISTINCT user_id 
            FROM rental_unit
        )
    """
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template("analytics_results.html",
                         title="Users Whose Listings Never Got Poor Reviews",
                         results=results)

# Route to handle user logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
