from flask import render_template, url_for, flash, redirect
from SkillAssessment.helpers import getSheets, getSheet
from SkillAssessment.analysis import Compare
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
    return render_template('about.html', title='Login')


@app.route("/register")
def register():
    return render_template('about.html', title='Lel')

@app.route("/kuanalysis/proxorcexamv1.1")
def showProxorCExamResults():
    SHEET_ID        = '15uyeG2oie6u-VHr7MhqzUVhYYLZ9JxLaFiYzLFx7Alg'
    MAIN_SHEET      = 'KU in Proxor C Exam'
    REFERENCE_SHEET = 'Appendix 2: Usage KU'

    # Fetch Google Sheets
    Sheets          = getSheets()
    main_sheet      = getSheet(Sheets, SHEET_ID, MAIN_SHEET)
    reference_sheet = getSheet(Sheets, SHEET_ID, REFERENCE_SHEET)

    metrics = Compare(main_sheet=main_sheet, reference_sheet=reference_sheet)

    return render_template('analysis.html', metrics=metrics)
