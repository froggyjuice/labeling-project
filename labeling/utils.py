import os
import json

def get_google_oauth_config():
    # manage.py 기준 상대경로
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client_id.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['web']
