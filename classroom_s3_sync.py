from __future__ import print_function
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import pandas as pd
import secrets
import pickle
import boto3
import os


# If modifying these scopes, delete the file token.pickle.
COURSE_ID       = '41106374079' # Test Value
TOKEN_HEX_PARAM = 4
MAPPINGS_FILE   = 'mappings.csv'
DATA_FOLDER     = 'data'
SCOPES          =   ['https://www.googleapis.com/auth/classroom.courses',
                     'https://www.googleapis.com/auth/classroom.student-submissions.students.readonly', 
                     'https://www.googleapis.com/auth/classroom.rosters',
                     'https://www.googleapis.com/auth/classroom.profile.emails']

# AWS Configurations
BUCKET_NAME     = 'soft-skill-assessment-project'


def encrypt(student_id):
    mapped_id = secrets.token_hex(4)

    # Update Student Id --> Random Number Mappings
    if (os.path.exists(MAPPINGS_FILE)):
        mappings = pd.read_csv(MAPPINGS_FILE, index_col=0)
        if len(mappings[mappings['Student Id'] == student_id]) != 0:        
            # Mapping already exists
            mapped_id = mappings[mappings['Student Id'] == student_id]['Mapped Id'].values[0]
        elif mappings[mappings['Mapped Id'] == mapped_id]:
            # `mapped_id` already exists, but mapped on some other `student_id`
            while len(mappings[mappings['Mapped Id'] == mapped_id]) != 0:
                mapped_id = secrets.token_hex(4)
        else:
            # Mappings doesn't exist, create new one
            mappings.loc[len(mappings)] = [student_id, mapped_id]
            mappings.to_csv(MAPPINGS_FILE)
    else:
        data = {'Student Id': [student_id], 'Mapped Id': [mapped_id]}
        mappings = pd.DataFrame(data)
        mappings.to_csv(MAPPINGS_FILE)
    return mapped_id


def getDrive():
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
    if os.path.exists('token_classroom.pickle'):
        with open('token_classroom.pickle', 'rb') as token:
            creds = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)

        with open('token_classroom.pickle', 'wb') as token:
            pickle.dump(creds, token, protocol=pickle.HIGHEST_PROTOCOL)

    service = build('classroom', 'v1', credentials=creds)
    return service


def getCourseList(classroom=None):
    if (classroom is None):
        classroom = getClassroom()
    courses = classroom.courses().list(pageSize=10).execute()['courses']

    for course in courses:
        print (course)


def uploadToS3(path, bucket=None):
    if bucket is None:
        raise Exception('No bucket object was passed. Terminating script.')

    for subdir, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(subdir, file)
            with open(full_path, 'rb') as data:
                bucket.put_object(Key=full_path[len(path)+1:], Body=data)

    print ("All Files and Subfolders in the path `{}` are uploaded to S3 Bucket.".format(path))


def downloadAssignment(submission, assignment, student_id, drive=None):
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
    # Google APIs
    classroom   = getClassroom()
    drive       = getDrive()
    s3          = boto3.resource('s3')
    bucket      = s3.Bucket(BUCKET_NAME)

    # getCourseList()

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

            downloadAssignment(submission['assignmentSubmission'], assignment['title'], encrypt(student['profile']['emailAddress'].split('@')[0]), drive=drive)

    uploadToS3(DATA_FOLDER, bucket=bucket)



if __name__ == '__main__':
    main()
