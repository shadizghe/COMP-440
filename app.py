from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import hashlib
import base64
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Function to connect to MySQL database
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="PASSWORD",  # Change this to your MySQL password
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

# Route for create listing/submit listing
@app.route("/create_listing", methods=["GET", "POST"])
def create_listing():
    if "username" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))
    
    username = session["username"]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        flash("User not found.")
        cursor.close()
        conn.close()
        return redirect(url_for("login"))

    user_id = user[0]

    cursor.execute("""
        SELECT COUNT(*) FROM rental_unit
        WHERE user_id = %s AND DATE(posted_at) = CURDATE()
    """, (user_id,))
    posted_today = cursor.fetchone()[0]
    listings_left = max(0, 2 - posted_today)

    if request.method == "POST":
        if listings_left <= 0:
            flash("You can only post 2 rental units per day.")
            cursor.close()
            conn.close()
            return render_template("create_listing.html", listings_left=listings_left)

        title = request.form["title"]
        details = request.form.get("description")
        features = request.form["features"]
        price = request.form["price"]

        cursor.execute("""
            INSERT INTO rental_unit (user_id, title, details, features, price)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, title, details, features, price))
        conn.commit()
        flash("Listing created successfully.")

        cursor.close()
        conn.close()
        return redirect(url_for("landing"))

    cursor.close()
    conn.close()
    return render_template("create_listing.html", listings_left=listings_left)


# Route for searching for listings
@app.route("/search_listing")
def search_listing():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    feature = request.args.get("feature")
    username = request.args.get("username")
    listings = []

    conn = connect_db()
    cursor = conn.cursor(dictionary=True)

    # Base query and parameters
    query = """
        SELECT rental_unit.id, rental_unit.title, rental_unit.details AS description,
               rental_unit.features, rental_unit.price, rental_unit.posted_at
        FROM rental_unit
        LEFT JOIN review ON rental_unit.id = review.rental_unit_id
        LEFT JOIN `user` ON rental_unit.user_id = `user`.id
        WHERE 1=1
    """
    params = []

    # If feature search is active
    if feature:
        query += " AND rental_unit.features LIKE %s"
        params.append(f"%{feature}%")
        query += " ORDER BY rental_unit.price DESC"
        cursor.execute(query, params)
        listings = cursor.fetchall()

    # If username search is active
    if username:
        query += """
            AND user.username = %s
            AND (review.rating = 'good' OR review.rating = 'excellent')
        """
        params.append(username)
        query += " ORDER BY rental_unit.price DESC"
        cursor.execute(query, params)
        listings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("search_listing.html", listings=listings)


# Route for leaving a review
@app.route("/submit_review", methods=["POST"])
def submit_review():
    if "username" not in session:
        flash("You must be logged in to leave a review.", "warning")
        return redirect(url_for("login"))

    rental_unit_id = request.form.get("listing_id")
    review_text = request.form.get("review_text")
    rating = request.form.get("rating")

    conn = connect_db()
    cursor = conn.cursor()

    # Get the current user ID
    cursor.execute("SELECT id FROM user WHERE username = %s", (session["username"],))
    user = cursor.fetchone()
    if not user:
        flash("Error: User not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("search_listing"))

    user_id = user[0]

    # Check if the listing belongs to this user
    cursor.execute("SELECT user_id FROM rental_unit WHERE id = %s", (rental_unit_id,))
    listing = cursor.fetchone()
    if not listing:
        flash("Error: Listing not found.", "danger")
    elif listing[0] == user_id:
        flash("Review denied: You cannot review your own listing.", "warning")
    else:
        # Checksif user already reviewed this listing
        cursor.execute("""
            SELECT COUNT(*) FROM review
            WHERE user_id = %s AND rental_unit_id = %s
        """, (user_id, rental_unit_id))
        if cursor.fetchone()[0] > 0:
            flash("You have already reviewed this listing.", "warning")
        else:
            # Checks if user has left 3 reviews today
            cursor.execute("""
                SELECT COUNT(*) FROM review
                WHERE user_id = %s AND DATE(posted_at) = CURDATE()
            """, (user_id,))
            reviews_today = cursor.fetchone()[0]

            if reviews_today >= 3:
                flash("You can only leave 3 reviews per day.", "warning")
            else:
                # Inserts the review
                cursor.execute("""
                    INSERT INTO review (rental_unit_id, user_id, rating, review_text)
                    VALUES (%s, %s, %s, %s)
                """, (rental_unit_id, user_id, rating, review_text))
                conn.commit()
                flash("Review submitted successfully!", "success")

    cursor.close()
    conn.close()
    return redirect(url_for("search_listing"))


# Route to handle user logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
