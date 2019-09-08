from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey12345' # Not the actual one

from SkillAssessment import routes
