CREATE TABLE rental_unit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    details TEXT,
    features VARCHAR(255),
    price DECIMAL(10, 2) NOT NULL,
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES user(id)
);