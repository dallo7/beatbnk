# import pandas as pd
# import time
#
# # Replace with the actual IP address or hostname where the Flask app is running
# api_url = 'http://192.168.88.248:5000/data'
#
# while True:
#     try:
#         print(f"Fetching data from {api_url}...")
#         # Pandas reads the CSV content directly from the URL
#         df = pd.read_csv(api_url)
#
#         print(f"Successfully fetched {len(df)} rows.")
#         # Perform your analysis on the DataFrame 'df'
#         if not df.empty:
#             print("Latest flight data sample:")
#             print(df.to_string())
#             # --- Add your analysis code here ---
#
#     except Exception as e:
#         print(f"Error fetching or reading data: {e}")
#
#     print("Waiting 60 seconds before next fetch...\n")
#     time.sleep(60) # Fetch data every minute


import requests
import json

# Define the URL of your Flask API endpoint
# Make sure the Flask app is running before running this script
api_url = "http://127.0.0.1:5000/save_data"

# Define the data you want to send as a Python dictionary
# This dictionary will be automatically converted to JSON by requests
data_to_send = {
    "name": "Alice Smith",
    "age": 30,
    "city": "New York"
}

print(f"Attempting to send data to {api_url}")
print(f"Data to send: {data_to_send}")

try:
    # Send a POST request to the API
    # The 'json' parameter automatically sets the Content-Type header to application/json
    # and serializes the dictionary to a JSON string.
    response = requests.post(api_url, json=data_to_send)

    # Check the status code of the response
    if response.status_code == 200:
        print("\nSuccessfully sent data!")
        # Print the response body from the API
        print("API Response:", response.json())
    else:
        print(f"\nFailed to send data. Status code: {response.status_code}")
        # Print the error message from the API, if available
        print("API Response:", response.text)

except requests.exceptions.ConnectionError:
    print(f"\nError: Could not connect to the API at {api_url}.")
    print("Please ensure your Flask application is running.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
