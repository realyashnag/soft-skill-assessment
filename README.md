# Software Developer Skill Assessment
Grand Idea is to create a model which, through expert-created examination's evaluation of a software developer, can predict their competency and skill level. Currently exploratory in nature.

## Assignment Sync
Script `classroom_s3_sync.py` downloads all the student submissions for all assignments of the mentioned course, and uploads them to S3 Bucket. 
1. **Enable Classroom API** from [here](https://developers.google.com/classroom/quickstart/python).
2. Download _credentials.json_ file from the above link and save it.
3. Install dependencies `pip install -r requirements.txt`.
4. Replace **COURSE_ID** in the script to target course's id.
5. Run the script from the same folder as the downloaded file.

Note: 
1. Course ID is hardcorded in the script.
2. AWS CLI must be configured to upload files to S3 Bucket.
