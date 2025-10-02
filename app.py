from flask import Flask, request, jsonify
import json

# Initialize the Flask application
app = Flask(__name__)

@app.route('/log_stk_initiation', methods=['POST'])
def log_stk_initiation():
    """
    Simulates the initiation log.
    It prints the received JSON payload and returns a success response.
    """
    data = request.get_json()

    # Print the full request body to the console
    print("--- STK Initiation Request Received ---")
    print(json.dumps(data, indent=2))
    print("--------------------------------------\n")

    # Return the status and body as requested
    return jsonify({
        "status": "Success",
        "message": "STK push initiation received and logged to console.",
        "body": data
    }), 201

@app.route('/mpesa_stk_callback', methods=['POST'])
def mpesa_stk_callback():
    """
    Handles the asynchronous M-Pesa callback.
    It prints the full callback body and returns a success acknowledgment.
    """
    callback_data = request.get_json()

    # Print the full callback body to the console
    print("--- M-Pesa Callback Received ---")
    print(json.dumps(callback_data, indent=2))
    print("-------------------------------\n")

    # M-Pesa requires a specific JSON response to acknowledge receipt.
    response_body = {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }
    
    # Return the status and the required M-Pesa response body
    return jsonify({
        "status": "Success",
        "message": "M-Pesa callback received and logged to console.",
        "body": response_body
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5800)
