CREATE TABLE IF NOT EXISTS review (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_unit_id INT NOT NULL,
    user_id INT NOT NULL,
    rating ENUM('excellent', 'good', 'fair', 'poor') NOT NULL,
    review_text TEXT NOT NULL,
    posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (rental_unit_id) REFERENCES rental_unit(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);
