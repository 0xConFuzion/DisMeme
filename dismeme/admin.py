import os
from flask import (
    Blueprint, render_template, g, redirect, url_for,
    request, abort, flash, current_app
)
from dismeme.db import get_db
from werkzeug.utils import secure_filename

bp = Blueprint('admin', __name__, url_prefix='/admin')
POSTS_PER_PAGE = 10

@bp.before_request
def restrict_to_admins():
    if not g.user or not g.user['is_admin']:
        abort(403)

@bp.route('/')
def dashboard():
    db = get_db()
    page = request.args.get('page', 1, type=int)

    users = db.execute('SELECT * FROM user').fetchall()

    total_posts = db.execute('SELECT COUNT(*) FROM post').fetchone()[0]
    offset = (page - 1) * POSTS_PER_PAGE

    posts = db.execute(
        '''
        SELECT p.id, title, body, created, author_id, username
        FROM post p JOIN user u ON p.author_id = u.id
        ORDER BY created DESC
        LIMIT ? OFFSET ?
        ''',
        (POSTS_PER_PAGE, offset)
    ).fetchall()

    reports = db.execute('''
        SELECT r.id, r.reason, r.post_id, r.user_id, u.username, p.title
        FROM report r
        JOIN user u ON r.user_id = u.id
        JOIN post p ON r.post_id = p.id
        ORDER BY r.id DESC
    ''').fetchall()

    total_pages = (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE

    return render_template(
        'admin/dashboard.html',
        users=users,
        posts=posts,
        reports=reports,
        page=page,
        total_pages=total_pages
    )

@bp.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    db = get_db()
    result = db.execute('SELECT body FROM post WHERE id = ?', (post_id,)).fetchone()

    if result:
        image_url = result['body']
        image_name = os.path.basename(image_url)
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_name)

        try:
            os.remove(image_path)
        except FileNotFoundError:
            pass

    db.execute('DELETE FROM post WHERE id = ?', (post_id,))
    db.commit()
    flash('Post deleted.')
    return redirect(url_for('admin.dashboard'))

@bp.route('/post/<int:post_id>/edit', methods=('GET', 'POST'))
def edit_post(post_id):
    db = get_db()
    post = db.execute(
        'SELECT p.id, title, body, created, author_id, username '
        'FROM post p JOIN user u ON p.author_id = u.id WHERE p.id = ?',
        (post_id,)
    ).fetchone()

    if post is None:
        abort(404)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']

        if not title:
            flash('Title is required.')
        else:
            db.execute(
                'UPDATE post SET title = ?, body = ? WHERE id = ?',
                (title, body, post_id)
            )
            db.commit()
            flash('Post updated.')
            return redirect(url_for('admin.dashboard'))

    return render_template('admin/edit_post.html', post=post)

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM user WHERE id = ?', (user_id,))
    db.commit()
    flash('User deleted.')
    return redirect(url_for('admin.dashboard'))
