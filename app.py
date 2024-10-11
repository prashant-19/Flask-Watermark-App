from flask import Flask, request, render_template, send_file, redirect, url_for, after_this_request
import os
import cv2
import zipfile
import uuid
import shutil
import threading
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Define paths for temporary storage
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load the watermark image
watermark_image = 'Watermark.png'
watermark_path = os.path.join(os.getcwd(), watermark_image)
watermark = cv2.imread(watermark_path)

if watermark is None:
    print(f"Error: Unable to load image from {watermark_path}")
else:
    print(f"Watermark loaded successfully from {watermark_path}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    for file in files:
        if file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print(f"Uploaded file: {filename}")
    return redirect(url_for('apply_watermark'))

@app.route('/apply_watermark')
def apply_watermark():
    alpha = 0.8
    processed_files = []
    output_dir = os.path.join(PROCESSED_FOLDER, str(uuid.uuid4()))
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            image = cv2.imread(file_path)
            if image is None:
                print(f"Error reading image {filename}")
                continue

            # Resize watermark if necessary
            if watermark.shape[:2] != image.shape[:2]:
                resized_watermark = cv2.resize(watermark, (image.shape[1], image.shape[0]))
            else:
                resized_watermark = watermark

            processed_image = cv2.addWeighted(image, 1, resized_watermark, 1 - alpha, 0)
            processed_image_path = os.path.join(output_dir, f'processed_{filename}')
            cv2.imwrite(processed_image_path, processed_image)
            processed_files.append(processed_image_path)
            print(f"Watermarked image saved: {processed_image_path}")

    # Create a ZIP file with processed images
    zip_path = os.path.join(PROCESSED_FOLDER, f"watermarked_images_{uuid.uuid4()}.zip")
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', output_dir)
    print(f"Zipped processed images to: {zip_path}")

    # Schedule cleanup after the response is sent
    @after_this_request
    def cleanup(response):
        # Clean up uploaded files
        for file in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, file)
            os.remove(file_path)
            print(f"Deleted uploaded file: {file}")

        # Clean up processed files and directory
        shutil.rmtree(output_dir)
        print(f"Deleted processed folder: {output_dir}")

        # Use a thread to delete the zip file after a short delay
        threading.Thread(target=delayed_delete, args=(zip_path,)).start()

        return response

    return send_file(zip_path, as_attachment=True, download_name='watermarked_images.zip', mimetype='application/zip')

def delayed_delete(file_path):
    time.sleep(5)  # Wait for 5 seconds before deleting
    try:
        os.remove(file_path)
        print(f"Deleted zip file: {file_path}")
    except Exception as e:
        print(f"Error deleting zip file: {e}")

if __name__ == "__main__":
    app.run()
