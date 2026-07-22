"""
Ground-truth eval set — verified by executing reference SQL directly
against the real European Soccer Database (database.sqlite). Each
expected answer was confirmed by hand, not guessed.

check types:
  "contains" — the final answer text should contain expected (case-insensitive)
  "numeric"  — a number within tolerance of expected should appear in the answer
"""

QUESTIONS = [
    {"question": "How many matches are in the database?",
     "expected": 25979, "check": "numeric", "tolerance": 0},
    {"question": "How many players are in the database?",
     "expected": 11060, "check": "numeric", "tolerance": 0},
    {"question": "How many leagues are in the database?",
     "expected": 11, "check": "numeric", "tolerance": 0},
    {"question": "Who is the tallest player in the database?",
     "expected": "Kristof van Hout", "check": "contains"},
    {"question": "Which league has the most matches played?",
     "expected": "Spain LIGA BBVA", "check": "contains"},
    {"question": "Which player has the highest average overall rating across all their attribute records?",
     "expected": "Lionel Messi", "check": "contains"},
    {"question": "Which team has the most home wins?",
     "expected": "FC Barcelona", "check": "contains"},
    {"question": "Which country has hosted the most matches?",
     "expected": "Spain", "check": "contains"},
    {"question": "Which team has scored the most total goals across all seasons, counting both home and away goals?",
     "expected": "FC Barcelona", "check": "contains"},
]
