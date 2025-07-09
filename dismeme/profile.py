from flask import (
    Blueprint, render_template, abort, request, redirect, url_for, flash, g
)
from dismeme.db import get_db
from dismeme.uploads import save_upload


bp = Blueprint('profile', __name__, url_prefix='/user')

@bp.route('/<username>')
def user_profile(username):
    db = get_db()
    user = db.execute(
        'SELECT id, username, bio, profile_pic FROM user WHERE username = ?', (username,)
    ).fetchone()

    if user is None:
        abort(404, "User not found.")

    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page

    posts = db.execute(
        'SELECT id, title, body, created FROM post WHERE author_id = ? ORDER BY created DESC LIMIT ? OFFSET ?',
        (user['id'], per_page, offset)
    ).fetchall()

    total_posts = db.execute(
        'SELECT COUNT(*) FROM post WHERE author_id = ?', (user['id'],)
    ).fetchone()[0]

    total_pages = (total_posts + per_page - 1) // per_page

    return render_template('/user/profile.html', user=user, posts=posts, page=page,
        total_pages=total_pages)

@bp.route('/edit', methods=('GET', 'POST'))
def edit_profile():
    if g.user is None:
        flash('You need to be logged in to edit your profile.')
        return redirect(url_for('auth.login'))

    db = get_db()

    if request.method == 'POST':
        bio = request.form['bio']
        file = request.files.get('profile_pic')

        filename, error = save_upload(file)

        if error:
            flash(error)
        else:
            if filename:
                db.execute(
                    'UPDATE user SET bio = ?, profile_pic = ? WHERE id = ?',
                    (bio, filename, g.user['id'])
                )
            else:
                db.execute(
                    'UPDATE user SET bio = ? WHERE id = ?',
                    (bio, g.user['id'])
                )
            db.commit()
            flash('Profile updated successfully.')
            return redirect(url_for('profile.user_profile', username=g.user['username']))

    user = db.execute(
        'SELECT bio, profile_pic FROM user WHERE id = ?', (g.user['id'],)
    ).fetchone()

    return render_template('/user/edit_profile.html', user=user)

@bp.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    if request.method == 'POST':
        if g.user is None:
            return redirect(url_for('index'))

        if g.user['id'] == id:
            db = get_db()
            db.execute('DELETE FROM user WHERE id = ?', (g.user['id'],))
            db.commit()
            flash('User Deleted.')
            return redirect(url_for('auth.logout'))
        else:
            abort(403)

    return redirect(url_for('index'))