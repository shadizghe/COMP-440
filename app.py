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
        password="Enrique40$",  # Change this to your MySQL password
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


# Route for creating a listing
@app.route("/create_listing")
def create_listing():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    username = session["username"]
    conn = connect_db()
    cursor = conn.cursor()

    # Get the user ID
    cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        flash("User not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("landing"))

    user_id = user[0]

    # Count today's listings
    cursor.execute("""
        SELECT COUNT(*) FROM rental_unit
        WHERE user_id = %s AND DATE(posted_at) = CURDATE()
    """, (user_id,))
    listings_today = cursor.fetchone()[0]
    listings_left = max(0, 2 - listings_today)

    cursor.close()
    conn.close()

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

    # Get the user ID
    cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        flash("User not found.", "danger")
        cursor.close()
        conn.close()
        return redirect(url_for("landing"))

    user_id = user[0]

    # Check how many listings the user has posted today
    cursor.execute("""
        SELECT COUNT(*) FROM rental_unit
        WHERE user_id = %s AND DATE(posted_at) = CURDATE()
    """, (user_id,))
    listings_today = cursor.fetchone()[0]

    if listings_today >= 2:
        flash("You can only post 2 listings per day.", "warning")
    else:
        # Insert new listing with current timestamp
        cursor.execute("""
            INSERT INTO rental_unit (user_id, title, details, features, price, posted_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (user_id, title, details, features, price))
        conn.commit()
        flash("Listing created successfully!", "success")

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
            ORDER BY price DESC
            """, (f"%{feature}%",))
        listings = cursor.fetchall()
        cursor.close()
        conn.close()

    username = request.args.get("username")

    if username:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ru.id, ru.title, ru.details, ru.features, ru.price, ru.posted_at
            FROM rental_unit ru
            JOIN user u ON ru.user_id = u.id
            WHERE u.username = %s
              AND ru.id IN (
                SELECT r.rental_unit_id
                FROM review r
                GROUP BY r.rental_unit_id
                HAVING SUM(r.rating IN ('poor', 'fair')) = 0
                   AND SUM(r.rating IN ('good', 'excellent')) > 0
            )
            ORDER BY ru.price DESC
        """, (username,))

        listings = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template("search_listing.html", listings=listings)

# Route for analytics page
@app.route("/analytics_results")
def analytics_menu():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    # No data; just show column headers and links
    return render_template(
        "analytics_results.html",
        title="Analytics Overview",
        overview=True  # flag to show menu
    )

# Route for most active posters
@app.route("/analytics_results/most_active_posters")
def most_active_posters():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    target_date = '2025-04-28'

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user.username, COUNT(rental_unit.id) AS post_count
        FROM rental_unit
        JOIN user ON rental_unit.user_id = user.id
        WHERE DATE(rental_unit.posted_at) = %s
        GROUP BY user.username
        ORDER BY post_count DESC
        LIMIT 3
    """, (target_date,))
    rows = cursor.fetchall()
    results = [f"{row[0]} - {row[1]} posts" for row in rows]

    return render_template(
        "analytics_results.html",
        title=f"Most Active Posters on {target_date}",
        data=results
    )

@app.route("/analytics/poor_reviewers")
def poor_reviewers():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user.username
        FROM user
        WHERE NOT EXISTS (
            SELECT 1
            FROM rental_unit
            JOIN review ON rental_unit.id = review.rental_unit_id
            WHERE rental_unit.user_id = user.id
              AND review.rating != 'poor'
        )
    """)
    rows = cursor.fetchall()
    results = [f"{row[0]}" for row in rows]

    return render_template("analytics_results.html", title="Poor Reviewers Only", data=results)


@app.route("/analytics/no_poor_reviews")
def no_poor_reviews():
    if "username" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.username
        FROM user u
        WHERE u.id NOT IN (
            SELECT ru.user_id
            FROM rental_unit ru
            JOIN review r ON r.rental_unit_id = ru.id
            WHERE r.rating = 'poor'
        )
    """)
    rows = cursor.fetchall()
    results = [f"{row[0]}" for row in rows]
    return render_template("analytics_results.html", title="No Poor Review Listings", data=results)


# Route to handle user logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/search_features", methods=["GET"])
def feature_search():
    users = None
    expensive_listings = []
    expensive_checked = False

    feature1 = request.args.get("feature1")
    feature2 = request.args.get("feature2")
    expensive_feature = request.args.get("expensive_feature")

    if feature1 and feature2:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT u.id, u.username
            FROM user u
            JOIN rental_unit ru1 ON u.id = ru1.user_id
            JOIN rental_unit ru2 ON u.id = ru2.user_id
            WHERE ru1.id != ru2.id
              AND DATE(ru1.posted_at) = DATE(ru2.posted_at)
              AND ru1.features LIKE %s
              AND ru2.features LIKE %s
        """, (f"%{feature1}%", f"%{feature2}%"))
        users = cursor.fetchall()
        cursor.close()
        conn.close()

    if expensive_feature:
        expensive_checked = True
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM rental_unit
            WHERE features LIKE %s
              AND price = (
                  SELECT MAX(price) FROM rental_unit
                  WHERE features LIKE %s
              )
        """, (f"%{expensive_feature}%", f"%{expensive_feature}%"))
        expensive_listings = cursor.fetchall()
        cursor.close()
        conn.close()

    return render_template(
        "search_features.html",
        users=users,
        expensive_listings=expensive_listings,
        expensive_checked=expensive_checked
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
