from flask import render_template, url_for, flash, redirect
from SkillAssessment import app

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html', title='Home')


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/login")
def login():
    return render_template('about.html', title='Lel')


@app.route("/register")
def register():
    return render_template('about.html', title='Lel')

