from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "aksdasdadkasdaspd"

client = MongoClient('mongodb://localhost:27017/')
db = client['chrysalis']
users_collection = db['users']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if users_collection.find_one({"username": username}):
            flash("Username already taken!")
            return redirect(url_for('signup'))

        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({
            "username": username,
            "email": email,
            "password": hashed_pw
        })
        
        flash("Registration successful! Please login.")
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password_candidate = request.form.get('password')
        user_data = users_collection.find_one({"username": username})

        if user_data and check_password_hash(user_data['password'], password_candidate):
            session['user'] = username
            return redirect(url_for('welcome'))
        else:
            flash("Invalid username or password")
    return render_template('login.html')

@app.route('/welcome')
def welcome():
    if 'user' in session:
        return render_template('welcome.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)