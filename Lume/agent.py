
import asyncio
import os
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
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
       - If user is in US/Canada: Call or text 988.
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

async def call_lume_async(query):
    APP_NAME = "lume_mental_health"
    USER_ID = "user123"
    SESSION_ID = "session456"

    session_service = InMemorySessionService()
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    
    content = types.Content(role='user', parts=[types.Part.from_text(text=query)])
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    async for event in events:
        if event.is_final_response():
            print("Lume Response: ", event.content.parts[0].text)

# Run the agent
if __name__ == "__main__":
    asyncio.run(call_lume_async("I've had a really long day and feel very overwhelmed."))