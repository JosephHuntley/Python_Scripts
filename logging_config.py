import logging
import os
from configparser import ConfigParser

def configure_logging():
    config_data = load_config()
    if config_data['server'] == 'prod':
        # Log to a file
        logging.basicConfig(filename='/home/Rasp/PyScript/log/ss.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    elif config_data['server'] == 'dev':
        # Log to the terminal
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')   

def load_config(file_path=None):
    if file_path is None:
        # If file_path is not provided, use the directory of the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, '../config.ini')
    config = ConfigParser()
    config.read(file_path)
    return config["credentials"]