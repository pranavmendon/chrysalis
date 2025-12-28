from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import asyncio
from datetime import datetime
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

safety_agent = Agent(
    name="safety_specialist",
    model="gemini-2.5-flash-lite",
    description="Mandatory agent for any mention of self-harm, suicide, or physical/mental harm.",
    instruction="""You are the Emergency Safety Module for Lume.
    
    CRITICAL PROTOCOL:
    1. DISCLOSURE: Immediately state: 'I am an AI, not a healthcare professional. I am here to help, but you should seek professional therapy or immediate medical attention.'
    2. HOTLINES: 
       - If user is in India: Vandrevala Foundation (9999666555) or AASRA (9820466726).
    3. TONE: Be calm, direct, and non-judgmental. Do not try to 'counsel' the user; focus on getting them to professional help.
    """
)

support_agent = Agent(
    name="support_specialist",
    model="gemini-2.5-flash-lite",
    description="Handles general empathetic conversation and emotional validation.",
    instruction="""You are the Empathy Module for Lume.
    
    CORE RULES:
    1. READABILITY: Never send a wall of text. Use bullet points and bold headers to separate thoughts.
    2. EMPATHY: Always validate the user's feelings first (e.g., 'It makes total sense that you feel [X]').
    3. PERSISTENCE: Stay supportive no matter what the user shares, unless it triggers a safety risk.
    """
)

root_agent = Agent(
    name="lume",
    model="gemini-2.5-flash-lite", 
    sub_agents=[safety_agent, support_agent], 
    description="Main coordinator that greets users and routes to Safety or Support specialists.",
    instruction="""You are Lume, an AI mental health companion (not a therapist).
    INTRODUCE YOURSELF AND YOUR ROLE AND ASK THE USER'S NAME
    Be as empathetic as possible.
    REAFFIRMATION: Use supportive cues like 'I hear how heavy that feels' or 'Im right here with you.'
    ACTIVE LISTENING: Reflect back what the user said to show you truly understand. 
   (e.g., 'It sounds like you're feeling [emotion] because [reason]. Is that right?') 
    DO NOT make your messages too long and hard for the user to read.
    
    FORMATTING: Use Markdown. Use bolding for validation and bullet points for complex thoughts.
    
    SAFETY: 
    1. If high distress is detected, provide the KIRAN (1800-599-0019) is available in 13 languages for India and break it to them in the most empathetic way possible by reaffirming them.
    2. Explicitly state you are an AI if the conversation gets deeply clinical.
    
    PERSONALIZATION: 
    - Store the user's name in session state and use it to lead every response.""")


app = Flask(__name__)
app.secret_key = "aksdasdadkasdaspd"

client = MongoClient('mongodb://localhost:27017/')
db = client['chrysalis']
chats_collection = db['chats']
users_collection=db['users']

session_service = InMemorySessionService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contactus')
def contactus():
    return render_template('contact.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if users_collection.find_one({"username": username}):
            flash("Username already taken!")
            return redirect(url_for('signup'))
        hashed_pw = generate_password_hash(password)
        users_collection.insert_one({
            "username": username,
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
            return redirect(url_for('main'))
        else:
            flash("Invalid username or password")
    return render_template('login.html')

@app.route('/main')
def main():
    if 'user' in session:
        return render_template('main.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user' in session:
        return render_template('profile.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/chatpage')
def chatpage():
    if 'user' in session:
        return render_template('chatpage.html', username=session['user'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

async def get_lume_response(username, query):
    APP_NAME = "lume_mental_health"
    try:
        await session_service.create_session(app_name=APP_NAME, user_id=username, session_id=f"session_{username}")
    except:
        pass
    
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    content = types.Content(role='user', parts=[types.Part.from_text(text=query)])
    events = runner.run_async(user_id=username, session_id=f"session_{username}", new_message=content)

    final_text = ""
    async for event in events:
        if event.is_final_response():
            final_text = event.content.parts[0].text
    return final_text

@app.route('/ask', methods=['POST'])
def ask():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    username = session['user']
    user_input = request.json.get('message')

    chats_collection.insert_one({
        "username": username,
        "role": "user",
        "content": user_input,
        "timestamp": datetime.utcnow()
    })

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ai_response = loop.run_until_complete(get_lume_response(username, user_input))
    loop.close()

    chats_collection.insert_one({
        "username": username,
        "role": "model",
        "content": ai_response,
        "timestamp": datetime.utcnow()
    })

    return jsonify({'response': ai_response})

@app.route('/chat')
def chat():
    if 'user' in session:
        history = list(chats_collection.find({"username": session['user']}).sort("timestamp", 1))
        return render_template('chat.html', username=session['user'], history=history)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)