from flask import Flask, request, render_template, send_file, redirect, url_for
import os
import cv2
import zipfile
import uuid
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return redirect(url_for('apply_watermark'))

@app.route('/apply_watermark')
def apply_watermark():
    # Use the original script logic for watermarking
    alpha = 0.8
    processed_files = []
    output_dir = os.path.join(PROCESSED_FOLDER, str(uuid.uuid4()))
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            image = cv2.imread(file_path)
            if image is None:
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

    # Create a ZIP file with processed images
    zip_path = os.path.join(PROCESSED_FOLDER, f"watermarked_images_{uuid.uuid4()}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in processed_files:
            zipf.write(file, os.path.basename(file))

    # Clean up uploaded files
    for file in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, file))

    return send_file(zip_path, as_attachment=True, download_name='watermarked_images.zip', mimetype='application/zip')

@app.after_request
def delete_processed_folders(response):
    # Clean up processed files and folders
    for folder in os.listdir(PROCESSED_FOLDER):
        folder_path = os.path.join(PROCESSED_FOLDER, folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                os.remove(os.path.join(folder_path, file))
            os.rmdir(folder_path)
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
