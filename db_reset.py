import os

DB_PATH = os.path.join('instance', 'brainburst.db')

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print('Deleted:', DB_PATH)
else:
    print('DB not found, nothing to delete:', DB_PATH)

