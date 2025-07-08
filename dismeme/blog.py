import os

from click import echo_via_pager
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort

from dismeme.auth import login_required
from dismeme.db import get_db
from dismeme.uploads import save_upload

POSTS_PER_PAGE = 9

bp = Blueprint('blog', __name__)


def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username '
        'FROM post p JOIN user u ON p.author_id = u.id '
        'WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post


@bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    db = get_db()

    total_posts = db.execute('SELECT COUNT(*) FROM post').fetchone()[0]
    offset = (page - 1) * POSTS_PER_PAGE

    posts = db.execute(
        '''
        SELECT p.id, title, body, tags, created, author_id, username, likes, dislikes
        FROM post p JOIN user u ON p.author_id = u.id
        ORDER BY created DESC
        LIMIT ? OFFSET ?
        ''',
        (POSTS_PER_PAGE, offset)
    ).fetchall()

    total_pages = (total_posts + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE

    return render_template(
        'blog/index.html',
        posts=posts,
        page=page,
        total_pages=total_pages
    )


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        file = request.files.get('file')
        tags = request.form['tags']

        filename, error = save_upload(file)

        if error:
            flash(error)
            return redirect(request.url)

        if not title:
            flash('Title is required.')
            return redirect(request.url)

        body = url_for('download_file', name=filename) if filename else ''

        db = get_db()
        db.execute(
            'INSERT INTO post (title, body, tags, author_id) VALUES (?, ?, ?, ?)',
            (title, body, tags, g.user['id'])
        )
        db.commit()
        return redirect(url_for('blog.index'))

    return render_template('blog/create.html')


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']

        if not title:
            flash('Title is required.')
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ? WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    result = db.execute('SELECT body FROM post WHERE id = ?', (id,)).fetchone()
    if result:
        image_url = result['body']
        image_name = os.path.basename(image_url)
        remove_img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_name)
        try:
            os.remove(remove_img_path)
        except FileNotFoundError:
            echo_via_pager('something wong')

    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


@bp.route('/<int:id>/like', methods=['POST'])
@login_required
def like_post(id):
    db = get_db()
    existing_vote = db.execute(
        'SELECT vote_type FROM post_vote WHERE post_id = ? AND user_id = ?',
        (id, g.user['id'])
    ).fetchone()

    if existing_vote is None:
        # New like
        db.execute(
            'INSERT INTO post_vote (post_id, user_id, vote_type) VALUES (?, ?, ?)',
            (id, g.user['id'], 'like')
        )
        db.execute('UPDATE post SET likes = likes + 1 WHERE id = ?', (id,))
    elif existing_vote['vote_type'] == 'dislike':
        # Change from dislike to like
        db.execute(
            'UPDATE post_vote SET vote_type = ? WHERE post_id = ? AND user_id = ?',
            ('like', id, g.user['id'])
        )
        db.execute('''
            UPDATE post
            SET likes = likes + 1,
                dislikes = dislikes - 1
            WHERE id = ?
        ''', (id,))
    else:
        flash('You already liked this post.')
        return redirect(request.referrer or url_for('blog.index'))

    db.commit()
    flash('Liked post!')
    return redirect(request.referrer or url_for('blog.index'))


@bp.route('/<int:id>/dislike', methods=['POST'])
@login_required
def dislike_post(id):
    db = get_db()
    existing_vote = db.execute(
        'SELECT vote_type FROM post_vote WHERE post_id = ? AND user_id = ?',
        (id, g.user['id'])
    ).fetchone()

    if existing_vote is None:
        # New dislike
        db.execute(
            'INSERT INTO post_vote (post_id, user_id, vote_type) VALUES (?, ?, ?)',
            (id, g.user['id'], 'dislike')
        )
        db.execute('UPDATE post SET dislikes = dislikes + 1 WHERE id = ?', (id,))
    elif existing_vote['vote_type'] == 'like':
        # Change from like to dislike
        db.execute(
            'UPDATE post_vote SET vote_type = ? WHERE post_id = ? AND user_id = ?',
            ('dislike', id, g.user['id'])
        )
        db.execute('''
            UPDATE post
            SET dislikes = dislikes + 1,
                likes = likes - 1
            WHERE id = ?
        ''', (id,))
    else:
        flash('You already disliked this post.')
        return redirect(request.referrer or url_for('blog.index'))

    db.commit()
    flash('Disliked post!')
    return redirect(request.referrer or url_for('blog.index'))


@bp.route('/<int:id>/report', methods=['POST', 'GET'])
@login_required
def report(id):
    db = get_db()

    if request.method == 'POST':
        reason = request.form['reason']
        if not reason:
            reason = 'No reason given.'

        # Check if this user has already reported this post
        existing = db.execute(
            'SELECT id FROM report WHERE post_id = ? AND user_id = ?',
            (id, g.user['id'])
        ).fetchone()

        if existing:
            flash('You have already reported this post.')
            return redirect(url_for('index'))

        # No previous report found; proceed to insert
        db.execute(
            'INSERT INTO report (post_id, user_id, reason) VALUES (?, ?, ?)',
            (id, g.user['id'], reason)
        )
        db.commit()

        flash('Post reported.')
        return redirect(url_for('index'))

    return render_template('user/report.html')

