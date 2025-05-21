from flask import Flask, request, jsonify
import json
import os

# Initialize the Flask application
app = Flask(__name__)

# Define the path to the file where data will be saved
# You can change 'user_data.txt' to your desired filename
DATA_FILE = 'user_data.txt'


@app.route('/save_data', methods=['POST'])
def save_user_data():
    """
    Receives JSON data from a POST request and saves it to a file.
    """
    # Get the JSON data from the request body
    data = request.get_json()

    # Check if data was received
    if not data:
        return jsonify({"error": "No data received"}), 400

    try:
        # Convert the received data (assuming it's a dictionary) to a JSON string
        # You could also just write the raw data string if preferred,
        # but saving as JSON lines makes it easier to parse later.
        data_string = json.dumps(data) + '\n'

        # Open the file in append mode ('a').
        # If the file doesn't exist, it will be created.
        with open(DATA_FILE, 'a') as f:
            f.write(data_string)

        # Return a success response
        return jsonify({"message": "Data saved successfully"}), 200

    except Exception as e:
        # Handle any potential errors during file writing or processing
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred while saving data"}), 500

# --- New GET endpoint ---
@app.route('/get_data', methods=['GET'])
def get_user_data():
    """
    Reads and returns all data stored in the data file.
    """
    # Check if the data file exists
    if not os.path.exists(DATA_FILE):
        return jsonify({"message": "No data file found"}), 404 # Not Found

    all_data = []
    try:
        with open(DATA_FILE, 'r') as f:
            for line in f:
                # Strip newline characters and parse each JSON line
                if line.strip(): # Ensure the line is not empty
                    all_data.append(json.loads(line.strip()))

        if not all_data:
            return jsonify({"message": "No data available"}), 200 # OK, but no content

        return jsonify(all_data), 200

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
        return jsonify({"error": "Error reading or parsing data file"}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred while retrieving data"}), 500


# Run the Flask app
# debug=True is useful for development, but should be False in production
if __name__ == '__main__':
    # The app will run on http://127.0.0.1:5000/ by default
    app.run(debug=True)
