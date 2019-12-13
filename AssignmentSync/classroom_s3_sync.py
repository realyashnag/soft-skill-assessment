#TODO: Deploy script on AWS Lambda

from __future__ import print_function
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import datetime
import secrets
import pickle
import shutil
import boto3
import gnupg
import os


# If modifying these scopes, delete the file token.pickle.
COURSE_ID               = '41106374079' # Test Value
TOKEN_HEX_PARAM         = 4
MAPPINGS_FILE           = 'mappings.csv'
DATA_FOLDER             = 'data'
SCOPES                  =  ['https://www.googleapis.com/auth/classroom.courses',
                            'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly', 
                            'https://www.googleapis.com/auth/classroom.rosters',
                            'https://www.googleapis.com/auth/classroom.profile.emails']

# AWS Configurations
BUCKET_NAME             = 'soft-skill-assessment-project'
CREDENTIALS_FILE_PATH   = 'client_secrets.json'
TARGET_EMAIL            = 'random@email.com'


def encrypt(filename):
    """
    Encrypt 'Mappings' file through public key of 'TARGET_EMAIL', and return the path of encrypted file.
    """
    gpg = gnupg.GPG()
    encrypted_filename = filename+'_'+ datetime.datetime.now().strftime("%d-%b-%Y_%I:%M%p") +'.gpg'

    print('~'*60)
    print("Encrypting File: {}".format(filename))
    with open(filename, 'rb') as f:
        status = gpg.encrypt_file(
                file=f,
                recipients=[TARGET_EMAIL],
                output=encrypted_filename
        )
    print("Operation Success: ", status.ok)
    print("File Encrypted using Public Key of {}".format(TARGET_EMAIL))
    print(status.status)
    print(status.stderr)
    print('~'*60)

    return encrypted_filename


def getMappings(student_id):
    """
    Returns a randomly generated string, 'mapped_id' to replace 'student_id'. Mappings from
    student_id --> random string is stored in 'mappings.csv'.
    """
    mapped_id = secrets.token_hex(4)

    try:
        mappings = pd.read_csv(MAPPINGS_FILE, index_col=0)
    except:
        data = {'Student Id': [], 'Mapped Id': []}
        mappings = pd.DataFrame(data)
        mappings.to_csv(MAPPINGS_FILE)

    # Update Student Id --> Random Number Mappings
    if student_id in list(mappings['Student Id']):
        # Mapping already exists
        mapped_id = mappings[mappings['Student Id'] == student_id]['Mapped Id'].values[0]
    else:
        # Mapping doesn't exist
        while mapped_id in list(mappings['Mapped Id']):
            # `mapped_id` already exists, but mapped on some other `student_id`
            mapped_id = secrets.token_hex(4)
        # Update mappings
        mappings.loc[len(mappings)] = [student_id, mapped_id]
        mappings.to_csv(MAPPINGS_FILE)
    return mapped_id


def getDrive():
    """
    Get Google Drive Object for Drive operations.
    """
    if os.path.exists('token_drive.pickle'):
        with open('token_drive.pickle', 'rb') as token:
            gauth = pickle.load(token)
    else:
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        with open('token_drive.pickle', 'wb') as token:
            pickle.dump(gauth, token, protocol=pickle.HIGHEST_PROTOCOL)

    service = GoogleDrive(gauth)
    return service


def getClassroom():
    """
    Get Google Classroom Object for Classroom navigation operations.
    """
    if os.path.exists('token_classroom.pickle'):
        with open('token_classroom.pickle', 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE_PATH, SCOPES)
        creds = flow.run_local_server(port=0)

        with open('token_classroom.pickle', 'wb') as token:
            pickle.dump(creds, token, protocol=pickle.HIGHEST_PROTOCOL)

    service = build('classroom', 'v1', credentials=creds)
    return service


def getCourseID(classroom=None):
    """
    Lists all the courses associated with the logged-in google classroom account. User 
    can choose which course's id to return. 
    """
    if (classroom is None):
        classroom = getClassroom()
    courses = classroom.courses().list(pageSize=10).execute()['courses']

    print ("Following are the list of courses associated with your account:")
    for i, course in enumerate(courses):
        print ("{}. {} | {} | {}".format(i+1, course['name'], course['courseState'], course['descriptionHeading']))

    print ("\nSelect (input the number of) the course you'd like to fetch data from...")
    selection = int(input())
    return courses[selection-1]['id']


def uploadToS3(path, bucket=None):
    """
    Uploads all subfolders of `DATA_FOLDER` folder to S3 Bucket
    """
    if bucket is None:
        raise Exception('No bucket object was passed. Terminating script.')

    if os.path.isfile(path):
        with open(path, 'rb') as data:
            bucket.put_object(Key=path, Body=data)
    else:
        for subdir, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(subdir, file)
                with open(full_path, 'rb') as data:
                    bucket.put_object(Key=full_path[len(path)+1:], Body=data)

    print ("All Files and Subfolders in the path `{}` are uploaded to S3 Bucket.".format(path))


def remove(arr):
    for path in arr:
        if os.path.isfile(path):
            print ("Deleting File '{}'".format(path))
            os.remove(path)
        else:
            print ("Deleting Tree '{}'".format(path))
            shutil.rmtree(path)


def downloadAssignment(submission, assignment, student_id, drive=None):
    """
    Downloads all attachments from submission per student, with respect to the assignmnet, before encrypting
    student ids.
    """
    try:
        os.makedirs(os.path.join(DATA_FOLDER, assignment, student_id))  # Create Directories
    except:
        pass

    if (drive is None):
        drive = getDrive()

    for attachment in submission['attachments']:
        try:
            article_id = attachment['driveFile']['id']
            drive_file = drive.CreateFile({'id': article_id})
            drive_file.GetContentFile(os.path.join(DATA_FOLDER, assignment, student_id, drive_file['title']))
        except Exception as e:
            raise Exception("Error in fetching user data | {}".format(str(e)))
    
    print ("\t\t ... Submissions Downloaded")


def main():
    """
    Task: Download all submissions from students (whose ids will be mapped with a random string) 
    to local storage, and then upload to S3 Bucket.
    """
    print ("~~~~~ Operation Started ~~~~~")

    # Google APIs
    classroom   = getClassroom()
    drive       = getDrive()
    s3          = boto3.resource('s3')
    bucket      = s3.Bucket(BUCKET_NAME)
    COURSE_ID   = getCourseID(classroom=classroom)

    courseWork = classroom.courses().courseWork().list(
            courseId=COURSE_ID).execute()['courseWork']

    print ("Fetching Assignments from the course...")
    for i, assignment in enumerate(courseWork):
        print ("{}. {}".format(i+1, assignment['title']))
        print ("\tFetching Student Submissions...")
        studentSubmissions = classroom.courses().courseWork().studentSubmissions().list(
                                courseId=assignment['courseId'], 
                                courseWorkId=assignment['id']
                            ).execute()['studentSubmissions']

        print ("\tFetching Student Details...")
        for j, submission in enumerate(studentSubmissions):
            student = classroom.courses().students().get(
                                    courseId=assignment['courseId'], userId=submission['userId']).execute()
            print ("\t{}. {} | {}".format(j+1, student['profile']['name']['fullName'], student['profile']['emailAddress']))

            downloadAssignment(submission['assignmentSubmission'], assignment['title'], getMappings(student['profile']['emailAddress'].split('@')[0]), drive=drive)

    encrypted_filename = encrypt(MAPPINGS_FILE)
    uploadToS3(encrypted_filename, bucket=bucket)
    uploadToS3(DATA_FOLDER, bucket=bucket)
    remove([MAPPINGS_FILE, DATA_FOLDER])

    print ("~~~~~ Operation Ended ~~~~~")


if __name__ == '__main__':
    main()

# -------------------------------- Commands ----------------------------------
# Enable API and Get credentials.json:
# https://developers.google.com/classroom/quickstart/python
#
# Generate KEY:
# gpg --gen-key
#
# Export KEY:
# gpg --armor --output mypubkey.gpg --export random@email.com
#
# Import KEY:
# gpg --import recipient-pubkey.gpg
#
# Decrypt FILE:
# gpg --output output_file_name.txt --decrypt file_to_decrypt.gpg


