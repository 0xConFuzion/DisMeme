from flask import Blueprint, render_template, g, redirect, url_for, request, abort
from dismeme.db import get_db

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.before_request
def restrict_to_admins():
    if not g.user or not g.user['is_admin']:
        abort(403)

@bp.route('/')
def dashboard():
    db = get_db()
    users = db.execute('SELECT * FROM user').fetchall()
    posts = db.execute('SELECT * FROM post ORDER BY created DESC').fetchall()
    return render_template('admin/dashboard.html', users=users, posts=posts)
