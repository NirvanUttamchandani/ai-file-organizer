import os
import json
import shutil
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import logging
import google.generativeai as genai

# --- Basic Setup ---
load_dotenv()
app = Flask(__name__, template_folder='.')
logging.basicConfig(level=logging.INFO)
MOVE_LOG_FILE = "move_log.json"

# --- Configure Google Gemini Client ---
try:
    # On Render, the API key will be an environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    logging.error(f"Failed to configure Google Gemini: {e}")
    model = None

# --- Core Functions ---
def scan_folder_contents(folder_path):
    """Scans a folder and returns a list of file paths and basic info."""
    files_info = []
    try:
        for root, _, files in os.walk(folder_path):
            for name in files:
                if name == MOVE_LOG_FILE:
                    continue
                full_path = Path(root) / name
                try:
                    stat = full_path.stat()
                    files_info.append({
                        "path": str(full_path),
                        "name": name,
                        "size_bytes": stat.st_size,
                        "created_at": stat.st_ctime,
                        "modified_at": stat.st_mtime
                    })
                except (FileNotFoundError, PermissionError) as e:
                    logging.warning(f"Could not access file {full_path}: {e}")
    except Exception as e:
        logging.error(f"Error scanning folder {folder_path}: {e}")
    return files_info

def get_ai_structure(files_info, user_prompt):
    """
    Sends file info and a prompt to the Gemini model to get a proposed folder structure.
    """
    if not model:
        return {"error": "Google Gemini API is not configured. Please check your API key."}

    simplified_file_list = [{"path": f["path"], "name": f["name"]} for f in files_info]

    prompt = f"""
    You are a meticulous file organization robot. Your ONLY task is to generate a valid JSON object that represents a file move plan.
    Your response MUST be ONLY the raw JSON object, starting with `[` and ending with `]`. Do not wrap it in markdown or any other text.

    **YOUR PRIMARY DIRECTIVE:**
    The user's instructions are the most important rule and MUST be followed precisely. The user's prompt OVERRIDES ALL default behaviors.

    **CRITICAL RULES:**
    1.  **USER INSTRUCTIONS FIRST:** Always analyze the user's prompt for specific folder names or grouping logic. If the user says "put all images and videos in a 'Media' folder", you MUST do that.
    2.  **DEFAULT BEHAVIOR (ONLY if no instructions):** If the user prompt is empty, organize files into common categories (e.g., Media, Documents, Archives, Others).
    3.  **JSON FORMAT:** The "destination" value must be a string in the format "FolderName/filename.ext".

    **EXAMPLE OF A PERFECT RESPONSE (Following User Instructions):**
    USER INSTRUCTION: "Put all pictures in a 'Holiday Snaps' folder and everything else in 'Miscellaneous'."
    JSON RESPONSE:
    [
      {{
        "source": "C:/Users/Test/Downloads/photo.jpg",
        "destination": "Holiday Snaps/photo.jpg"
      }},
      {{
        "source": "C:/Users/Test/Downloads/report.pdf",
        "destination": "Miscellaneous/report.pdf"
      }}
    ]

    ---
    Now, based on the following file list and user instructions, generate the JSON move plan.
    File list: {json.dumps(simplified_file_list, indent=2)}
    User Instructions: "{user_prompt if user_prompt else 'Organize by file type.'}"
    """

    try:
        logging.info("Sending request to Google Gemini API...")
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

def execute_move_plan(base_folder, move_plan):
    """Executes the file moves and logs them for rollback."""
    # This function is designed for a desktop app and will not work on a web server.
    # The logic remains as a reference for the desktop version of the app.
    return {"success": False, "message": "File moving is a desktop-only feature and is disabled on the web server."}


# --- API Routes ---
@app.route('/')
def index():
    # Note: The web version is a demo. The core value is the API.
    return "<h1>AI File Organizer API</h1><p>This server provides the AI logic for the file organizer application. The file scanning and moving functionality is intended for the desktop client.</p>"

@app.route('/api/get-structure', methods=['POST'])
def get_structure_route():
    data = request.json
    # In a real web app, you'd get the file list from the request, not by scanning a local path.
    files_info_from_client = data.get('files_info')
    user_prompt = data.get('prompt', '')

    if not files_info_from_client:
        return jsonify({"error": "No file information provided."}), 400

    proposed_structure = get_ai_structure(files_info_from_client, user_prompt)
    if "error" in proposed_structure:
        return jsonify(proposed_structure), 500
    return jsonify(proposed_structure)

# The execute and rollback routes are disabled as they don't apply to a web server environment.
# They manipulate a local file system, which doesn't exist in the same way here.
@app.route('/api/execute-moves', methods=['POST'])
def execute_moves_route():
    return jsonify({"success": False, "message": "This operation is not supported on the web server."}), 403

@app.route('/api/rollback', methods=['POST'])
def rollback_route():
    return jsonify({"success": False, "message": "This operation is not supported on the web server."}), 403

if __name__ == '__main__':
    # This part is for local development only. Render will use Gunicorn to run the app.
    app.run(host='0.0.0.0', port=5001, debug=False)

