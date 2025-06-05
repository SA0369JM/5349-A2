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

from flask import Flask, render_template, request
import boto3
import os
import pymysql
import json

app = Flask(__name__)

# S3 Configuration
S3_BUCKET = 'image-caption-jshi0843a2'
THUMBNAIL_PREFIX = 'thumbnails/'
s3 = boto3.client('s3')

# Function to retrieve RDS credentials from AWS Secrets Manager
def get_rds_secrets(secret_name):
    region_name = "us-east-1"  
    client = boto3.client('secretsmanager', region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None

# Load secrets from Secrets Manager
def get_rds_connection():
    try:
        secret = get_rds_secrets('rdsSecret')
        if not secret:
            print("Failed to load RDS Secret")
            return None
        return pymysql.connect(
            host=secret['host'],
            user=secret['username'],
            password=secret['password'],
            database='image_caption_db'
        )
    except Exception as e:
        print(f"DB connect error: {e}")
        return None

# Route: Home page with upload form
@app.route('/')
def index():
    return render_template('index.html')

# Route: Handle image upload to S3
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        filename = file.filename
        key = f"uploads/{filename}"
        try:
            s3.upload_fileobj(file, S3_BUCKET, key)
            file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
            return render_template('upload.html', file_url=file_url, caption="Please wait while the caption is generated.")
        except Exception as e:
            return render_template('upload.html', error="Failed to upload image.")
    return render_template('upload.html', error="No file selected")

# Route: Display uploaded images with thumbnails and captions
@app.route("/gallery")
def gallery():
    conn = get_rds_connection()
    if not conn:
        return render_template("gallery.html", error="Cannot connect to RDS.")

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT image_key, caption FROM captions ORDER BY uploaded_at DESC")
            records = cursor.fetchall()
    except Exception as e:
        return render_template("gallery.html", error="DB query failed")

    images = []
    for row in records:
        image_key = row[0]
        caption = row[1]
        thumbnail_key = THUMBNAIL_PREFIX + image_key.split("/")[-1]
        image_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_key}"
        images.append({'url': image_url, 'caption': caption})

    return render_template("gallery.html", images=images)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)