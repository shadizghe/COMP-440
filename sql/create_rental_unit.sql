CREATE TABLE rental_unit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    details TEXT,
    price DECIMAL(10, 2),
    posted_at DATETIME,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES user(id)
);