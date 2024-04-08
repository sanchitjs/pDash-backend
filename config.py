from flask import Flask
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials,db

cred = credentials.Certificate("credentials.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://test-35f13-default-rtdb.firebaseio.com/"})

app = Flask(__name__)
app.secret_key = "PhotomTechnologies"
CORS(app, resources={r"*": {"origins": "https://pdash-photom.netlify.app"}})