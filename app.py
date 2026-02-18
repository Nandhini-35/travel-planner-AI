import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None
    print("WARNING: GEMINI_API_KEY not found in .env file. Chat-bot will not work until key is provided.")

SYSTEM_PROMPT = """
You are an expert AI Travel Planner. Your goal is to help users plan their trips by gathering necessary details and then creating a comprehensive itinerary.

**Your Process:**
1.  **Greeting & Gathering Info:** Start by greeting the user. If they haven't provided details, ask for:
    -   Destination (if not decided, ask for preferences like beach, mountains, city, etc.)
    -   Duration of the trip (how many days)
    -   Number of travelers (and if there are kids/seniors)
    -   Budget (low, medium, high)
    -   Interests (food, adventure, history, relaxation, etc.)
    *Do not ask all questions at once. Ask 1-2 questions at a time to keep the conversation natural.*

2.  **Refinement:** Once you have the basics, suggest a few broad options or confirm their choice. Ask about pacing (relaxed vs. packed) or specific must-see spots.

3.  **Itinerary Generation:** When you have sufficient information, generate a day-by-day itinerary.
    -   Be specific about places to visit.
    -   Suggest times for visits.
    -   Include restaurant or food recommendations.
    -   Mention estimated costs if possible.

4.  **Formatting:** Use Markdown for the itinerary to make it readable (bold headings, bullet points).

**Tone:**
Friendly, enthusiastic, professional, and helpful.
"""

@app.route("/", methods=["GET"])
def index():
    # Clear session history on reload to start fresh, or keep it. Let's keep it for now but maybe add a clear button.
    if "chat_history" not in session:
        session["chat_history"] = []
    return render_template("index.html") # We will replace index.html with the chat interface

@app.route("/chat", methods=["POST"])
def chat():
    if not model:
        return jsonify({"error": "API Key is missing. Please configure GEMINI_API_KEY in .env file."}), 500

    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Retrieve history from session
    history = session.get("chat_history", [])
    
    # Construct the full prompt context
    # Gemini Pro is stateless via API unless using ChatSession object, but here we can just append history manually for simplicity or use start_chat
    # Let's use the list of messages format
    
    gemini_history = []
    # Add system prompt as the first part of context (simulated as user/model turn or just pre-prompt)
    # Gemini Pro API handles system instructions differently in newer versions, 
    # but a robust way for 'gemini-pro' is to prepend it to the first user message or keep it as context.
    # We will simulate a chat session.
    
    # Re-build chat object
    chat_session = model.start_chat(history=gemini_history)
    
    # Add previous history to the chat session manually if needed, or just manage context string.
    # The `history` list in session is [{'role': 'user', 'text': ...}, {'role': 'model', 'text': ...}]
    
    # We need to convert session history to Gemini's expected format if we want to use `start_chat` with history,
    # or we can just send the full context as a prompt.
    # `start_chat` is cleaner.
    
    formatted_history = []
    # Add System Prompt implicit context
    # formatted_history.append({'role': 'user', 'parts': [SYSTEM_PROMPT]})
    # formatted_history.append({'role': 'model', 'parts': ["Understood. I am your AI Travel Planner. How can I help you today?"]})
    
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        formatted_history.append({'role': role, 'parts': [msg["text"]]})

    try:
        chat = model.start_chat(history=formatted_history)
        
        # If this is the very first message and history is empty, prepend the system prompt logic
        final_message = user_message
        if not history:
            final_message = SYSTEM_PROMPT + "\n\nUser: " + user_message
        
        response = chat.send_message(final_message)
        ai_response_text = response.text
        
        # Update session history
        history.append({"role": "user", "text": user_message})
        history.append({"role": "model", "text": ai_response_text})
        session["chat_history"] = history
        
        return jsonify({"response": ai_response_text})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear_chat():
    session.pop("chat_history", None)
    return jsonify({"status": "success"})

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == "__main__":
    app.run(debug=True)
