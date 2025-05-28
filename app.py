from flask import Flask, request, jsonify
import json
import psycopg2
from psycopg2 import sql
import datetime

# Initialize the Flask application
app = Flask(__name__)

# --- Database Configuration ---
DB_HOST = "beatbnk-db.cdgq4essi2q1.ap-southeast-2.rds.amazonaws.com"
DB_PORT = "5432"
DB_USER = "user"
DB_PASSWORD = "X1SOrzeSrk"
DB_NAME = "beatbnk_db"

# --- M-Pesa Specific Configuration ---
TABLE_NAME = "mpesa_stk_push_payments"

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_value_from_callback_metadata(metadata_items, key_name):
    """Helper function to extract a value from M-Pesa callback metadata."""
    if metadata_items:
        for item in metadata_items:
            if item.get("Name") == key_name:
                return item.get("Value")
    return None

@app.route('/log_stk_initiation', methods=['POST'])
def log_stk_initiation():
    """
    Logs the initial response from M-Pesa after an STK Push request is made.
    Expects a JSON payload
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    required_fields = ["MerchantRequestID", "CheckoutRequestID", "ResponseCode", "ResponseDescription", "CustomerMessage"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cur = conn.cursor()

        insert_query = sql.SQL("""
            INSERT INTO {} (
                merchant_request_id, checkout_request_id, initial_response_code,
                initial_response_description, initial_customer_message,
                initial_api_response_payload, paymentStatus
            ) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """).format(sql.Identifier(TABLE_NAME))

        cur.execute(
            insert_query,
            (
                data["MerchantRequestID"],
                data["CheckoutRequestID"],
                data["ResponseCode"],
                data["ResponseDescription"],
                data["CustomerMessage"],
                json.dumps(data),
                "Pending"
            )
        )

        inserted_id = cur.fetchone()[0]
        conn.commit()
        cur.close()

        return jsonify({"message": "STK push initiation logged successfully", "id": inserted_id, "checkoutRequestID": data["CheckoutRequestID"]}), 201

    except psycopg2.Error as e:
        print(f"Database error during STK initiation logging: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "An internal error occurred while logging STK initiation"}), 500
    except Exception as e:
        print(f"An error occurred during STK initiation logging: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "An unexpected internal error occurred"}), 500
    finally:
        if conn:
            conn.close()

@app.route('/mpesa_stk_callback', methods=['POST'])
def mpesa_stk_callback():
    """
    Handles the asynchronous callback from M-Pesa.
    Updates the transaction record based on the callback data.
    """
    callback_data = request.get_json()

    if not callback_data or "Body" not in callback_data or "stkCallback" not in callback_data["Body"]:
        print(f"Invalid callback data received: {callback_data}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid callback data format"}), 400

    stk_callback = callback_data["Body"]["stkCallback"]
    merchant_request_id = stk_callback.get("MerchantRequestID")
    checkout_request_id = stk_callback.get("CheckoutRequestID")
    result_code = str(stk_callback.get("ResultCode", ""))
    result_desc = stk_callback.get("ResultDesc", "No description")

    if not checkout_request_id:
        print(f"Callback missing CheckoutRequestID: {stk_callback}")
        return jsonify({"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}), 400

    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("Database connection failed while processing callback.")

            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        cur = conn.cursor()

        # Determine payment status
        payment_status = "Failed"
        if result_code == "0":
            payment_status = "Success"
        elif result_code == "1032":
            payment_status = "UserCancelled"
        elif result_code == "1":
             payment_status = "InsufficientFunds"


        transaction_code = None
        transaction_amount = None
        transaction_date = None
        phone_number = None

        callback_metadata_items = None
        if "CallbackMetadata" in stk_callback and "Item" in stk_callback["CallbackMetadata"]:
            callback_metadata_items = stk_callback["CallbackMetadata"]["Item"]
            if result_code == "0":
                transaction_amount_str = get_value_from_callback_metadata(callback_metadata_items, "Amount")
                if transaction_amount_str is not None:
                    try:
                        transaction_amount = float(transaction_amount_str)
                    except ValueError:
                        print(f"Could not parse transaction amount: {transaction_amount_str}")
                        transaction_amount = None

                transaction_code = get_value_from_callback_metadata(callback_metadata_items, "MpesaReceiptNumber")
                transaction_date = get_value_from_callback_metadata(callback_metadata_items, "TransactionDate")
                phone_number = get_value_from_callback_metadata(callback_metadata_items, "PhoneNumber")


        update_query = sql.SQL("""
            UPDATE {} SET
                callbackResponseMessage = %s,
                callbackPayload = %s,
                paymentStatus = %s,
                transactionCode = %s,
                transactionAmount = %s,
                callback_result_code = %s,
                transaction_date = %s,
                phone_number = %s,
                callback_received_at = %s,
                updated_at = %s
            WHERE checkout_request_id = %s
        """).format(sql.Identifier(TABLE_NAME))

        current_timestamp = datetime.datetime.now(datetime.timezone.utc)

        cur.execute(
            update_query,
            (
                result_desc,
                json.dumps(stk_callback),
                payment_status,
                transaction_code,
                transaction_amount,
                result_code,
                transaction_date,
                phone_number,
                current_timestamp,
                current_timestamp,
                checkout_request_id
            )
        )

        if cur.rowcount == 0:

            print(f"No record found to update for CheckoutRequestID: {checkout_request_id}")
            conn.rollback()

            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted (but no matching transaction found to update)"}), 200
        else:
            conn.commit()
            print(f"Callback for CheckoutRequestID {checkout_request_id} processed successfully.")

        cur.close()

        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

    except psycopg2.Error as e:
        print(f"Database error during M-Pesa callback processing for {checkout_request_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted (internal processing error)"}), 200
    except Exception as e:
        print(f"An unexpected error occurred during M-Pesa callback for {checkout_request_id}: {e}")
        if conn:
            conn.rollback()
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted (unexpected internal error)"}), 200
    finally:
        if conn:
            conn.close()

@app.route('/get_payment_records', methods=['GET'])
def get_payment_records():
    """
    Reads and returns all M-Pesa payment records from the database.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        select_query = sql.SQL("SELECT * FROM {} ORDER BY created_at DESC").format(
            sql.Identifier(TABLE_NAME)
        )
        cur.execute(select_query)
        rows = cur.fetchall()
        cur.close()

        all_records = []
        for row in rows:
            record = dict(row)
            for key in ['initial_api_response_payload', 'callbackPayload']:
                if key in record and isinstance(record[key], str):
                    try:
                        record[key] = json.loads(record[key])
                    except json.JSONDecodeError:
                        pass
            for key, value in record.items():
                if isinstance(value, datetime.datetime):
                    record[key] = value.isoformat()
                elif isinstance(value, datetime.date):
                     record[key] = value.isoformat()

            all_records.append(record)

        if not all_records:
            return jsonify({"message": "No payment records available"}), 200

        return jsonify(all_records), 200

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Error retrieving payment records from DB"}), 500
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred while retrieving records"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Ensure your PostgreSQL table 'mpesa_stk_push_payments' is created

    """
    CREATE TABLE IF NOT EXISTS mpesa_stk_push_payments (
        id SERIAL PRIMARY KEY,
        merchant_request_id VARCHAR(255) NOT NULL,
        checkout_request_id VARCHAR(255) NOT NULL UNIQUE,
        initial_response_code VARCHAR(10),
        initial_response_description TEXT,
        initial_customer_message TEXT,
        initial_api_response_payload JSONB,
        paymentStatus VARCHAR(50) DEFAULT 'Pending', -- e.g., Pending, Success, Failed, UserCancelled
        callback_received_at TIMESTAMP WITH TIME ZONE,
        callback_result_code VARCHAR(10),
        callbackResponseMessage TEXT,      -- From ResultDesc
        callbackPayload JSONB,             -- Full STKCallback
        transactionCode VARCHAR(50),       -- M-Pesa Receipt Number
        transactionAmount NUMERIC(12, 2),
        transaction_date VARCHAR(20),      -- From callback metadata item "TransactionDate"
        phone_number VARCHAR(20),          -- From callback metadata item "PhoneNumber"
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Optional: Trigger to auto-update 'updated_at' timestamp
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
       NEW.updated_at = NOW();
       RETURN NEW;
    END;
    $$ language 'plpgsql';

    CREATE TRIGGER update_mpesa_stk_push_payments_updated_at
    BEFORE UPDATE ON mpesa_stk_push_payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
    """
    app.run(debug=True, port=5000)
