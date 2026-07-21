"""
Project 3 test set — each task requires chaining at least 2 tool calls.
expected: the correct numeric answer, tolerance: how close counts as correct.
"""

TASKS = [
    {
        "task": "What is the combined population (in millions) of the two most populous cities in Brazil?",
        "expected": 12.33 + 6.32,
        "tolerance": 0.5,
    },
    {
        "task": "What is the population of Argentina's capital city, Buenos Aires, plus the population of Córdoba?",
        "expected": 3.12 + 1.43,
        "tolerance": 0.5,
    },
    {
        "task": "Which has a higher combined population: Colombia's top two cities, or Peru's top two cities? Give the higher combined total in millions.",
        "expected": max(7.97 + 2.57, 10.09 + 1.09),
        "tolerance": 0.5,
    },
    {
        "task": "What is Chile's GDP in trillions plus Peru's GDP in trillions?",
        "expected": 0.34 + 0.24,
        "tolerance": 0.05,
    },
    {
        "task": "What is the population of Lima minus the population of Arequipa, in millions?",
        "expected": 10.09 - 1.09,
        "tolerance": 0.5,
    },
    {
        "task": "What is the combined GDP of Brazil and Argentina, in trillions?",
        "expected": 2.13 + 0.64,
        "tolerance": 0.1,
    },
    {
        "task": "What is the population of Medellín plus the population of Cali, in millions?",
        "expected": 2.57 + 2.23,
        "tolerance": 0.5,
    },
    {
        "task": "What is Santiago's population multiplied by 2, in millions?",
        "expected": 6.16 * 2,
        "tolerance": 0.5,
    },
]
