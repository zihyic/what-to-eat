-- =====================================================================
-- What To Eat!! — sample seed data so the app runs out of the box
-- Load after schema.sql:  mysql -u root -p what_to_eat < seed.sql
-- =====================================================================

USE what_to_eat;

-- Users (role-based access control demo)
INSERT INTO Users (Username, Role) VALUES
  ('admin', 'admin'),
  ('guest', 'general');

-- Ingredients
INSERT INTO Ingredient (IngrdName) VALUES
  ('Chicken Breast'), ('Eggs'), ('Milk'), ('Rice'), ('Soy Sauce'),
  ('Tomato'), ('Pasta'), ('Cheese'), ('Ground Beef'), ('Broccoli'),
  ('Salmon'), ('Avocado'), ('Tortilla'), ('Black Beans'), ('Ramen Noodles');

-- Meal options (EatOut = FALSE means cook-at-home recipes)
INSERT INTO `Option` (MealName, EatOut, CuisineType, Mood) VALUES
  ('Chicken Fried Rice', FALSE, 'Chinese',  'cozy'),
  ('Margherita Pasta',   FALSE, 'Italian',  'comfort'),
  ('Salmon Poke Bowl',   FALSE, 'Japanese', 'fresh'),
  ('Beef Tacos',         TRUE,  'Mexican',  'fun'),
  ('Sushi Platter',      TRUE,  'Japanese', 'celebratory'),
  ('Tomato Soup',        FALSE, 'American', 'cozy');

-- Restaurants
INSERT INTO Restaurant (RstrntName) VALUES
  ('Taco Fiesta'), ('Tokyo Bay'), ('Golden Wok');

-- Fridge: what the demo user currently has
INSERT INTO Fridge (IngrdID, Qty) VALUES
  (1, 2),    -- Chicken Breast x2
  (2, 12),   -- Eggs x12
  (3, 1),    -- Milk x1
  (4, 5),    -- Rice x5
  (5, 1),    -- Soy Sauce x1
  (6, 4),    -- Tomato x4
  (7, 2),    -- Pasta x2
  (8, 1);    -- Cheese x1

-- Recipes: (OptID, IngrdID, Qty, Optional)
INSERT INTO Recipe (OptID, IngrdID, Qty, Optional) VALUES
  -- Chicken Fried Rice
  (1, 1, 1, FALSE), (1, 2, 2, FALSE), (1, 4, 2, FALSE), (1, 5, 1, TRUE),
  -- Margherita Pasta
  (2, 7, 1, FALSE), (2, 6, 3, FALSE), (2, 8, 1, FALSE),
  -- Salmon Poke Bowl
  (3, 11, 1, FALSE), (3, 4, 1, FALSE), (3, 12, 1, TRUE),
  -- Tomato Soup
  (6, 6, 5, FALSE), (6, 3, 1, FALSE), (6, 8, 1, TRUE);

-- Menus: (RstrntID, OptID, Price)
INSERT INTO Menu (RstrntID, OptID, Price) VALUES
  (1, 4, 9.99),    -- Taco Fiesta serves Beef Tacos
  (2, 5, 24.99),   -- Tokyo Bay serves Sushi Platter
  (2, 3, 14.99),   -- Tokyo Bay also serves Salmon Poke Bowl
  (3, 4, 8.99);    -- Golden Wok serves Beef Tacos
