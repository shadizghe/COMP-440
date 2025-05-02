CREATE TABLE rental_unit_features (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_unit_id INT,
    feature_name VARCHAR(255),
    FOREIGN KEY (rental_unit_id) REFERENCES rental_unit(id)
);