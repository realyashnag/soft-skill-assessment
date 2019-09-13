from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = 'TotallyNotTheSecretKey' # Not the actual one

from SkillAssessment import routes
