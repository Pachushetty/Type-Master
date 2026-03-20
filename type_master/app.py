from flask import Flask, render_template, jsonify
import random

app = Flask(__name__)

PASSAGES = [
    "the quick brown fox jumps over the lazy dog and runs away fast",
    "python is a great programming language used by millions of developers",
    "technology makes our life easier and more comfortable every single day",
    "reading books every day helps you learn new things and grow your mind",
    "practice makes perfect when you work hard you will always improve",
    "the sun rises in the east and sets in the west every single day",
    "a journey of a thousand miles begins with a single small step forward",
    "life is short so make the most of every moment you have each day",
    "hard work and dedication will always lead you to success in life",
    "the best way to predict your future is to create it yourself today",
    "learning to type fast is a very useful skill in the modern digital world",
    "every expert was once a beginner who never gave up on their goals",
    "success is not final failure is not fatal it is the courage to continue",
    "the more that you read the more things you will know and understand",
    "believe you can and you are already halfway there keep going forward"
]

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_passage")
def get_passage():
    return jsonify({"passage": random.choice(PASSAGES)})

if __name__ == "__main__":
    app.run(debug=True)
