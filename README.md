# RNG Roller Game

A web-based RNG rolling game with user authentication and inventory management.

## Features

- User registration and login system
- Probabilistic RNG system (1 in 2, 1 in 3, 1 in 4, etc. infinitely)
- 10-second cooldown on rolls (enforced by API)
- Inventory system that tracks all rolls
- Inventory sorted by rarity (rarest first)

## Setup Instructions

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## How to Play

1. Register a new account or login
2. Click the "Roll RNG" button to get a random rarity
3. Wait for the 10-second cooldown between rolls
4. Your rolls are automatically saved to your inventory
5. View your inventory sorted by rarest items at the bottom

## RNG System

The RNG system works probabilistically:
- 1 in 2 chance (50%) to get "1 in 2"
- 1 in 3 chance (33.33%) to get "1 in 3"
- 1 in 4 chance (25%) to get "1 in 4"
- And so on infinitely...

Each rarity is rolled sequentially until one succeeds, making rarer items progressively harder to obtain.

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Session-based with password hashing
