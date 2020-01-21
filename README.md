# Software Developer Skill Assessment
Grand Idea is to create a model which, through expert-created examination's evaluation of a software developer, can predict their competency and skill level. Currently exploratory in nature.

## Web Application
Hosted on AWS EC2 (Free Tier), can be found here - [Website Link](http://18.191.227.197/).

## Assignment Sync
Script `classroom_s3_sync.py` downloads all the student submissions for all assignments of the mentioned course, and uploads them to S3 Bucket. 
1. **Enable Classroom API** from [here](https://developers.google.com/classroom/quickstart/python).
2. Download _credentials.json_ file from the above link, rename it to _client_secrets.json_ and save it in the script folder.
3. Install dependencies `pip install -r requirements.txt`.
4. Create Key Value Pairs using GPG with your Details (Note that these will be saved in the System)
    ```
    gpg --gen-key
    ```
5. Configure AWS CLI for S3 Bucket
6. The Script requires either of the 2 command line arguments: `--enrypt` (Download assignments, encrypt Mappings and Upload to S3) or `--decrypt` (Decrypt encrypted Mappinngs)
    ```
    python classroom_download.py --encrypt --email "random@email.com" 

    # or

    python classroom_download.py --decrypt --file "mappings.csv_20-Jan-2020.gpg" --passphrase "temp1234"
    ```
7. __NOTE:__ In the first run, use '--encrypt'. After the Mappings file has been created and encrypted, use '--decrypt' to first decrypt the file before running the encryption job again. 


Downloads will be in the ___DATA_FOLDER___  ('__data__' by default) of in the root directory.
