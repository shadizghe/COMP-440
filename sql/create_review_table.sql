CREATE TABLE IF NOT EXISTS review (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_unit_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    rating VARCHAR(20) NOT NULL,  -- can be 'excellent', 'good', 'fair', 'poor'
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rental_unit_id) REFERENCES rental_unit(id),
    FOREIGN KEY (reviewer_id) REFERENCES user(id)
);