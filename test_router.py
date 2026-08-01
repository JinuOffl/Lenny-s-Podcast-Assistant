import sys
sys.path.insert(0, 'backend')
from router import classify_skill

tests = [
    ('What did Brian Chesky say about culture?', 'qa'),
    ('How do the best growth teams measure success?', 'qa'),
    ('Generate a list of retention frameworks', 'qa'),
    ('Build a case for product-led growth', 'qa'),
    ('Make a table comparing growth strategies', 'qa'),
    ('Render the key lessons from the podcast', 'qa'),
    ('Write a Ship30for30 essay on PMF', 'ship30for30'),
    ('Write an article about retention', 'ship30for30'),
    ('Write me an essay about Chesky', 'ship30for30'),
    ('Create an HTML dashboard of growth frameworks', 'artifact'),
    ('Build me a landing page for a growth tool', 'artifact'),
    ('Generate html for a summary page', 'artifact'),
    ('Create a chart of retention metrics', 'artifact'),
    ('Build a dashboard showing key metrics', 'artifact'),
    ('Make an interactive visualization', 'artifact'),
]

passed = 0
failed = 0
for msg, expected in tests:
    got = classify_skill(msg)
    status = 'PASS' if got == expected else 'FAIL'
    if got != expected:
        failed += 1
        print(f'{status}: "{msg}" -> got={got}, want={expected}')
    else:
        passed += 1

print(f'\n{passed}/{len(tests)} passed, {failed} failed')
