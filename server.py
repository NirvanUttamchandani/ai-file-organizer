import os
import json
import shutil
import time
from pathlib import Path
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import google.generativeai as genai

# --- Basic Setup ---
load_dotenv()
app = Flask(__name__) # Removed template_folder since it's not needed
logging.basicConfig(level=logging.INFO)
MOVE_LOG_FILE = "move_log.json"

# --- Configure Google Gemini Client ---
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    # --- UPDATED: Switched to the more powerful 'gemini-2.5-pro' model ---
    model = genai.GenerativeModel('gemini-2.5-pro')
    # --- END UPDATE ---
except Exception as e:
    logging.error(f"Failed to configure Google Gemini: {e}")
    model = None

# --- This function is no longer used by the server, but the logic is sound ---
def scan_folder_contents(folder_path):
    pass # This function is now handled by the Electron app's main.js

def get_ai_structure(files_info, user_prompt):
    """
    Sends file info (now including dates) and a prompt to the Gemini model.
    """
    if not model:
        return {"error": "Google Gemini API is not configured. Please check your API key."}

    # We no longer need to simplify the file list, the AI can use the dates
    # simplified_file_list = [{"path": f["path"], "name": f["name"]} for f in files_info]

    # --- UPDATED: New, more intelligent prompt ---
    prompt = f"""
    You are a hyper-intelligent file organization expert. Your ONLY task is to generate a valid JSON object that represents a file move plan.
    Your response MUST be ONLY the raw JSON object, starting with `[` and ending with `]`. Do not wrap it in markdown or any other text.

    **YOUR PRIMARY DIRECTIVE:**
    The user's prompt is your absolute command. You MUST follow it precisely, even if it overrides your default logic. Analyze the prompt for keywords related to grouping, dates (year, month), or content (e.g., "invoices", "reports").

    **FILE DATA ANALYSIS:**
    You will be given a list of files. For each file, you have:
    - "path": The original location. This MUST be the value for the "source" key in your JSON.
    - "name": The filename. Use this to infer content (e.g., "report.pdf" is a document).
    - "created_at" / "modified_at": These are timestamps. Use them if the user asks for date-based organization (e.g., "organize by year").

    **CRITICAL RULES:**
    1.  **USER PROMPT IS LAW:** If the user says "put images and videos in 'Media'", you MUST do that. Do not create separate 'Images' and 'Videos' folders.
    2.  **DEFAULT BEHAVIOR (No User Prompt):** If the prompt is empty, your default is to organize by common file types (e.g., Images, Documents, Videos, Audio, Archives, Others).
    3.  **JSON FORMAT:** The "destination" value must be a string in the format "FolderName/filename.ext". Do not use backslashes.

    **EXAMPLE (Date-based organization):**
    USER INSTRUCTION: "Organize my files by the year they were modified."
    FILE: {{ "path": "C:/path/doc.pdf", "name": "doc.pdf", "modified_at": 1678886400000 }}
    JSON RESPONSE:
    [
      {{
        "source": "C:/path/doc.pdf",
        "destination": "2023/doc.pdf"
      }}
    ]

    ---
    Now, based on the following file list and user instructions, generate the JSON move plan.
    File list: {json.dumps(files_info, indent=2)}
    User Instructions: "{user_prompt if user_prompt else 'Organize by file type.'}"
    """
    # --- END UPDATE ---

    try:
        logging.info("Sending request to Google Gemini API (gemini-2.5-pro)...")
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Clean the response to ensure it's valid JSON
        start_index = response_text.find('[')
        end_index = response_text.rfind(']')
        if start_index != -1 and end_index != -1:
            json_str = response_text[start_index:end_index+1]
            logging.info(f"Extracted JSON string from Gemini: {json_str}")
            move_plan = json.loads(json_str)
            return move_plan
        else:
            raise ValueError("No valid JSON list found in Gemini response.")

    except Exception as e:
        logging.error(f"An error occurred with the Google Gemini API call: {e}")
        return {"error": str(e)}

# --- This function is no longer used by the server, but the logic is sound ---
def execute_move_plan(base_folder, move_plan):
    pass # This function is now handled by the Electron app's main.js

# --- API Routes ---
@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "AI Organizer Backend (gemini-2.5-pro) is running."})

@app.route('/api/get-structure', methods=['POST'])
def get_structure_route():
    data = request.json
    files_info = data.get('files_info')
    user_prompt = data.get('prompt', '')

    if not files_info:
        return jsonify({"error": "No files info provided."}), 400
    
    proposed_structure = get_ai_structure(files_info, user_prompt)
    if "error" in proposed_structure:
        return jsonify(proposed_structure), 500
    return jsonify(proposed_structure)

# --- These routes are no longer used by the Electron app but are harmless to keep ---
@app.route('/api/execute-moves', methods=['POST'])
def execute_moves_route():
    return jsonify({"error": "This endpoint is deprecated. Execute moves on the client."}), 404

@app.route('/api/rollback', methods=['POST'])
def rollback_route():
    return jsonify({"error": "This endpoint is deprecated. Rollback on the client."}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)