#TODO: Deploy script on AWS Lambda

from __future__ import print_function
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import argparse
import datetime
import secrets
import pickle
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
TARGET_EMAIL            = 'philip.miller@lnmiit.ac.in' # Default Value for Recipient Email, Is overridden by '--email' argument's value


def encrypt(filename):
    """
    Encrypt 'Mappings' file, which can be unlocked only through private key of 'TARGET_EMAIL', and return the path of encrypted file.
    """
    gpg = gnupg.GPG()
    encrypted_filename = filename+'_'+ datetime.datetime.now().strftime("%d-%b-%Y") +'.gpg'


    print('~'*60)
    print("Encrypting File: {} using Public Key of {}".format(filename, TARGET_EMAIL))
    with open(filename, 'rb') as f:
        status = gpg.encrypt_file(
                file=f,
                recipients=[TARGET_EMAIL],
                output=encrypted_filename
        )
    print("Operation Success: ", status.ok)
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


def decrypt(filepath, passphrase):
    """
    Decrypt passed 'filepath' and output decrypted file. Note that the recipient's private key must be present in the system.
    """

    print('~'*60)

    gpg = gnupg.GPG()
    with open(filepath, 'rb') as f:
        status = gpg.decrypt_file(f, 
                    passphrase=passphrase, 
                    output='mappings.csv')
    print (status.ok)
    print (status.status)
    print (status.stderr)
    print('~'*60)


if __name__ == '__main__':
    # Passed arguments handling
    parser = argparse.ArgumentParser(description='Google Classroom Handler')
    parser.add_argument('-e','--email', help='Email of the Recipient (Public Key of the recipient must exist in the system)')
    parser.add_argument('-f', '--file', help='Path for the file to be decrypted')
    parser.add_argument('-p', '--passphrase', help='Passphrase for Decryption.')
    parser.add_argument('--encrypt', help='Download assignments and perform encryption', action='store_true')
    parser.add_argument('--decrypt', help='Perform decryption of the passsed file (-f Argument required)', action='store_true')
    args = parser.parse_args()

    print ("~~~~~ Operation Started ~~~~~")

    TARGET_EMAIL = str(args.email).strip()

    if (args.encrypt):
        # Encrypt Task
        if (args.email == '' or args.email is None):
            # No Email is Passed
            print ("No Receipient Email was passed. Use '--email' to pass Recipient's Email.")
            print ("~~~~~ Operation Ended ~~~~~")
            quit()
        else:
            print ("Proceeding with Downloading Assignments, Creating/Updating and Encrypting Mappings and Uploading to S3 Bucket.\n")
            main()
    elif (args.decrypt):
        # Decrypt Task
        if (args.file == '' or args.file is None or args.passphrase == '' or args.passphrase is None):
            # No File is Passed
            print ("No File Path or Passphrase was passed. Use '--path' to pass the file and '--passphrase' to pass your passphrase for the file to be decrypted.")
            print ("~~~~~ Operation Ended ~~~~~")
            quit()
        else:
            print ("Proceeding with Decrypting passed file.\n")
            decrypt(str(args.file).strip(), str(args.passphrase).strip())
    else:
        print ("No Task argument passed. Use '--encypt' or '-decrypt' to perform respective operations.")

    print ("~~~~~ Operation Ended ~~~~~")


# ---------------------------------- Steps -----------------------------------
# - Generate Key/Value pair using GPG Command Line
# - Setup AWS CLI
# - Run the script (Encryption)
# - Before re-running the 'encrypt' script, run 'decrypt' script to decrypt 'Mappings.csv' and then re-run the 'encrypt' script
#

# -------------------------------- Commands ----------------------------------
# 
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
#
# List KEYS:
# gpg --list-secret-keys --keyid-format LONG
# 


# ------------------------------ Usage Exaamples -----------------------------
# 
# For Encryption:
# python classroom_download.py --encrypt --email "random@email.com"
#
# For Decryption:
# python classroom_download.py --decrypt --file "mappings.csv_21-Jan-2020.gpg" --passphrase "temp1234"
#
