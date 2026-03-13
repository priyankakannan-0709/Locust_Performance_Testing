import csv
import random

def load_users(file_path):
    users = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            users.append(row)
    return users

def get_random_user(users):
    return random.choice(users)
