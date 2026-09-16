-- =====================================================================
-- What To Eat!! — database schema
-- Implements the relational design from the project report:
--   6 normalized tables (BCNF) + Users table for role-based access control
-- Engine: MySQL 8.0+ (CHECK constraints enforced)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS what_to_eat
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE what_to_eat;

-- ---------------------------------------------------------------------
-- Entity tables
-- ---------------------------------------------------------------------

CREATE TABLE Ingredient (
  IngrdID   INT AUTO_INCREMENT PRIMARY KEY,
  IngrdName VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- NOTE: `Option` is a reserved word in MySQL, hence the backticks.
CREATE TABLE `Option` (
  OptID       INT AUTO_INCREMENT PRIMARY KEY,
  MealName    VARCHAR(100) NOT NULL,
  EatOut      BOOLEAN NOT NULL DEFAULT FALSE,
  CuisineType VARCHAR(50),
  Mood        VARCHAR(50)
) ENGINE=InnoDB;

CREATE TABLE Restaurant (
  RstrntID   INT AUTO_INCREMENT PRIMARY KEY,
  RstrntName VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

-- Users table supporting role-based access control (see report § Security).
-- Admins may add/update/delete ingredients, recipes and options;
-- general users may only view options and manage their own fridge.
CREATE TABLE Users (
  UserID   INT AUTO_INCREMENT PRIMARY KEY,
  Username VARCHAR(50) NOT NULL UNIQUE,
  Role     ENUM('admin', 'general') NOT NULL DEFAULT 'general'
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- Relationship tables
-- ---------------------------------------------------------------------

-- Fridge: which ingredients the user currently has and in what quantity.
-- (User is conceptual only per the E-R diagram, so no UserID is stored.)
CREATE TABLE Fridge (
  IngrdID INT PRIMARY KEY,
  Qty     DECIMAL(10, 2) NOT NULL DEFAULT 0,
  CONSTRAINT chk_fridge_qty_nonnegative CHECK (Qty >= 0),
  CONSTRAINT fk_fridge_ingredient
    FOREIGN KEY (IngrdID) REFERENCES Ingredient (IngrdID)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Recipe: ingredients required for each meal option.
CREATE TABLE Recipe (
  OptID    INT NOT NULL,
  IngrdID  INT NOT NULL,
  Qty      DECIMAL(10, 2) NOT NULL,
  Optional BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (OptID, IngrdID),
  CONSTRAINT chk_recipe_qty_nonnegative CHECK (Qty >= 0),
  CONSTRAINT fk_recipe_option
    FOREIGN KEY (OptID) REFERENCES `Option` (OptID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_recipe_ingredient
    FOREIGN KEY (IngrdID) REFERENCES Ingredient (IngrdID)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Menu: which meal options each restaurant serves, and at what price.
CREATE TABLE Menu (
  RstrntID INT NOT NULL,
  OptID    INT NOT NULL,
  Price    DECIMAL(8, 2) NOT NULL,
  PRIMARY KEY (RstrntID, OptID),
  CONSTRAINT chk_menu_price_nonnegative CHECK (Price >= 0),
  CONSTRAINT fk_menu_restaurant
    FOREIGN KEY (RstrntID) REFERENCES Restaurant (RstrntID)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_menu_option
    FOREIGN KEY (OptID) REFERENCES `Option` (OptID)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;
