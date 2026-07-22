"""
Project 6 test set — refund requests with a known expected_trigger label
(should this genuinely require human review?), so we can measure whether
our trigger logic gets it right, not just whether the demo "looks fine."
"""

REQUESTS = [
    {"text": "Customer wants a $15 refund for a duplicate small item charge, clear duplicate on the receipt.", "expected_trigger": False},
    {"text": "Customer requesting a $45 refund because the product arrived damaged, photo attached.", "expected_trigger": False},
    {"text": "Customer wants a $1,200 refund for an enterprise annual plan, citing dissatisfaction.", "expected_trigger": True},
    {"text": "Customer disputes a $22 charge saying they don't recognize it at all.", "expected_trigger": False},
    {"text": "Customer wants a $600 refund for a laptop stand claiming it never arrived, no tracking info provided.", "expected_trigger": True},
    {"text": "Customer requesting refund for a $9.99 subscription month, says they forgot to cancel.", "expected_trigger": False},
    {"text": "Customer wants $350 back for a conference ticket, claims event was cancelled but provides no evidence.", "expected_trigger": True},
    {"text": "Customer wants a $30 refund, order clearly shows a billing error on our end, receipt matches.", "expected_trigger": False},
    {"text": "Customer wants a $2,500 refund for a bulk order claiming it was 'not as described'.", "expected_trigger": True},
    {"text": "Customer wants $18 back for a shipping fee that was charged twice by mistake, logs confirm double charge.", "expected_trigger": False},
]
