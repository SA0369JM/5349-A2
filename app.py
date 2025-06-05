"""
COMP5349 Assignment: Image Captioning App using Gemini API and AWS Services

IMPORTANT:
Before running this application, ensure that you update the following configurations:
1. Replace the GEMINI API key (`GOOGLE_API_KEY`) with your own key from Google AI Studio.
2. Replace the AWS S3 bucket name (`S3_BUCKET`) with your own S3 bucket.
3. Update the RDS MySQL database credentials (`DB_HOST`, `DB_USER`, `DB_PASSWORD`).
4. Ensure all necessary dependencies are installed by running the provided setup script.

Failure to update these values will result in authentication errors or failure to access cloud services.
"""

# To use on an AWS Linux instance
# #!/bin/bash
# sudo yum install python3-pip -y
# pip install flask
# pip install mysql-connector-python
# pip install -q -U google-generativeai
# pip install boto3 werkzeug
# sudo yum install -y mariadb105

from flask import Flask, request, render_template, redirect
import boto3
import pymysql
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)

# AWS Config
S3_BUCKET = 'image-caption-bucket-jshi0843' 
REGION_NAME = 'us-east-1'

# RDS Config
DB_HOST = 'database-1.csjynfw96ond.us-east-1.rds.amazonaws.com'
DB_USER = 'admin'
DB_PASSWORD = 'comp5349'
DB_NAME = 'image_caption_db'

# Gemini API key (from environment variable)
GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GOOGLE_API_KEY:
    print("[WARNING] GEMINI_API_KEY not set — captioning will not work if called.")

# Boto3 S3 client
s3 = boto3.client('s3', region_name=REGION_NAME)

def connect_rds():
    try:
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"[ERROR] RDS connection failed: {e}")
        raise

@app.route('/')
def index():
    try:
        connection = connect_rds()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM captions ORDER BY uploaded_at DESC")
            images = cursor.fetchall()
    except Exception as e:
        print(f"[ERROR] Failed to load captions: {e}")
        images = []
    finally:
        if 'connection' in locals():
            connection.close()

    return render_template('index.html', images=images, s3_bucket=S3_BUCKET)

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return redirect('/')

    image = request.files['image']
    if image.filename == '':
        return redirect('/')

    filename = secure_filename(image.filename)
    image_key = f"uploads/{filename}"

    # Upload to S3
    try:
        s3.upload_fileobj(image, S3_BUCKET, image_key)
    except Exception as e:
        print(f"[ERROR] Failed to upload to S3: {e}")
        return "S3 upload failed", 500

    # Insert metadata into RDS
    try:
        connection = connect_rds()
        with connection.cursor() as cursor:
            sql = "INSERT INTO captions (image_key, caption) VALUES (%s, %s)"
            cursor.execute(sql, (image_key, ""))  # Empty caption to be filled by Lambda
        connection.commit()
    except Exception as e:
        print(f"[ERROR] Failed to insert into RDS: {e}")
        return "Database error", 500
    finally:
        if 'connection' in locals():
            connection.close()

    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
