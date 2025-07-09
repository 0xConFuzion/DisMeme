# SECRET_KEY should be a random secret string for security
SECRET_KEY = 'dev'

# Path to the SQLite database file inside instance folder
DATABASE = 'dismeme.sqlite'

# Folder where uploads will be saved (absolute or relative path)
UPLOAD_FOLDER = '/home/Fuzion/PycharmProjects/neonhaze/dismeme/static/uploads'

NAME_LENGTH = 9

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

POSTS_PER_PAGE = 9