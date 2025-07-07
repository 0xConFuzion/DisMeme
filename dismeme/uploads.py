import os
import string
import random
from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename):
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def gen_file_name(extension=''):
    chars = string.ascii_letters + string.digits
    name_length = current_app.config['NAME_LENGTH']

    if not isinstance(name_length, int):
        name_length = 9

    rand_str = ''.join(random.choices(chars, k=name_length))

    return f"{rand_str}.{extension}" if extension else rand_str


def save_upload(file):
    if file and file.filename != '':
        if allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not upload_folder:
                raise RuntimeError("UPLOAD_FOLDER is not configured")

            while True:
                filename = secure_filename(gen_file_name(ext))
                full_path = os.path.join(upload_folder, filename)
                if not os.path.exists(full_path):
                    break

            file.save(full_path)
            return filename, None
        else:
            return None, 'Invalid image format. Allowed types: png, jpg, jpeg, gif.'
    return None, None  # no file provided
