from flask import Flask, request, jsonify
import logging
import os
import time
import random

app = Flask(__name__)

# Setup basic logging for the listener
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simulate failure probability (0.0 to 1.0)
FAILURE_RATE = float(os.getenv("WEBHOOK_FAILURE_RATE", 0.0))
# Simulate a delay for processing webhook
WEBHOOK_PROCESSING_DELAY = float(os.getenv("WEBHOOK_PROCESSING_DELAY", 0.0))

@app.route('/webhook-receiver', methods=['POST'])
def webhook_receiver():
    payload = request.json
    attack_id = payload.get('attack_id', 'N/A')
    event_type = payload.get('event_type', 'N/A')
    
    logger.info(f"Webhook received: {event_type} for attack {attack_id}")

    time.sleep(WEBHOOK_PROCESSING_DELAY)

    if os.getenv("ALWAYS_FAIL_WEBHOOK", "false").lower() == "true":
        logger.warning(f"Simulating forced failure for webhook {attack_id}")
        return jsonify({"status": "failed", "message": "Simulated forced failure"}), 500
    
    if random.random() < FAILURE_RATE:
        logger.warning(f"Simulating random failure for webhook {attack_id}")
        return jsonify({"status": "failed", "message": "Simulated random failure"}), 500

    logger.info(f"Webhook successfully processed for attack {attack_id}")
    return jsonify({"status": "success", "message": "Webhook received successfully"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "webhook-listener"}), 200

if __name__ == '__main__':
    port = int(os.getenv("FLASK_PORT", 8003))
    app.run(host='0.0.0.0', port=port, debug=False)
