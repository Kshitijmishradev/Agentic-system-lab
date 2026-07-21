"""
Project 1 test set — 30 raw support tickets.
Mix of clean (easy to categorize) and messy (sarcasm, ambiguity, rants,
multi-issue) tickets. The messy ones are what actually cause validation
failures — that's the point, don't swap them for easy ones.
"""

TICKETS = [
    # --- clean, unambiguous ---
    "I was charged twice for my subscription this month. Please refund the extra charge.",
    "The app crashes every time I try to upload a photo larger than 5MB.",
    "Can you add dark mode to the mobile app? Would love that feature.",
    "I can't log into my account, it says my password is wrong even after reset.",
    "Thank you so much for the quick fix last week, everything works great now!",
    "My invoice from last month shows the wrong billing address, please correct it.",
    "The export-to-CSV button does nothing when I click it on the reports page.",
    "I'd like to request a feature to bulk-delete old messages.",
    "How do I change the email associated with my account?",
    "Your service went down for 3 hours yesterday and cost us a client meeting. Unacceptable.",

    # --- messy / ambiguous / sarcastic ---
    "oh great, another update that broke the search bar. cool cool cool. anyway can someone fix it",
    "so i tried cancelling my sub like 3 times now and it keeps charging me?? this is actually insane",
    "not sure if this is a bug or im just dumb but the dashboard numbers dont match my spreadsheet at all",
    "love the product overall!! just wish theres a way to export data to excel not just pdf. also billing page loads slow",
    "URGENT!!! system down cant process payroll due today need help NOW",
    "eh its fine i guess, works most of the time. sometimes logs me out randomly tho",
    "why is my card being declined when there's clearly money in the account, is this a known issue or",
    "hey quick q — can multiple team members share one login or does everyone need separate accounts",
    "this used to work fine last month now every time i hit save it just spins forever, no error nothing",
    "not mad just confused lol, got billed for premium but i thought i downgraded to basic in march",
    "the new UI is honestly a downgrade, everything takes 3 more clicks than before. can we get the old one back",
    "account got locked after i changed my phone number, support bot wasnt helpful at all, need a human pls",
    "guessing this is a long shot but is there any chance of a discount for annual plans, cash flow is tight rn",
    "app worked fine on wifi but completely unusable on cellular data, times out constantly",
    "im honestly about to cancel, third time this month the export feature just silently fails no error msg",
    "quick feedback - loading spinner is way too slow, otherwise no complaints, keep up good work",
    "getting a weird error code E4521 when trying to sync calendar, googled it and found nothing",
    "asked for a refund two weeks ago, still nothing, starting to feel ignored here",
    "not urgent but the settings page has a typo, says 'Notifcations' instead of Notifications",
    "everything about this platform is slow and buggy and I regret upgrading to the pro plan honestly",
]
