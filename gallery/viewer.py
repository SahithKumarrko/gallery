import math
import os
from pathlib import Path
import platform
import random
import re
import string
import time
from turtle import pos
from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request, url_for
)
import magic
import requests
from tqdm import tqdm
from werkzeug.exceptions import abort
from datetime import datetime
from gallery.auth import login_required
from gallery.db import get_db
from hurry.filesize import size, alternative

bp = Blueprint('gallery', __name__)
bp_files = Blueprint('files', __name__, static_folder="contents", static_url_path="/contents")
SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
path = str(Path(__file__).resolve().parent) + "/contents/"
n_cols = 5
@bp.route('/')
def index():
    if g.user is not None:
        db = get_db()
        posts = db.execute(
            'SELECT *'
            ' FROM post'
            ' ORDER BY created DESC limit 3'
        ).fetchall()
        print("Posts :: ",len(posts))
        final = []
        for p in posts:
            final.append({'id':p["id"],"author_id":p["author_id"],"created":p["created"],"title":p["title"],"file_path":p["file_path"],"persons":p["persons"],"file_size":p["file_size"],"file_type":p["file_type"]})
    
        return render_template('gallery/index.html', posts=final, base_url = request.base_url,is_favorites = False)
    return redirect(url_for("auth.login"))


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    d = None
    if platform.system() == 'Windows':
        d = os.path.getmtime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            d = stat.st_mtime
        except AttributeError:
            pass
    if d is not None:
        return datetime.fromtimestamp(d).strftime("%d/%m/%Y %H:%M %p")
    else:
        return datetime.now().strftime("%d/%m/%Y %H:%M %p")

@bp.route('/favorite/<int:id>', methods=('GET',))
@login_required
def favorite(id):
    db = get_db()
    res = []
    res = db.execute(
                f'Select * from favorites where favorite_id="{id}"',
            ).fetchall()
    if len(res) == 0:
        db.execute(
                    f'INSERT INTO favorites (favorite_id) VALUES ("{id}")'
                )
        db.commit()
        print("Saved")
    return {'status':200}

@bp.route('/remove-favorite/<int:id>', methods=('GET',))
@login_required
def remove_favorite(id):
    db = get_db()
    db.execute(f'DELETE From favorites where favorite_id={id}')
    db.commit()
    print("Saved")
    return {'status':200}

@bp.route('/load-more/<int:from_row>/<int:offset>/<string:t>', methods=('GET',))
@login_required
def load_more(from_row,offset,t):
    print("Loading more for :: ",t , from_row)
    posts = []
    db = get_db()
    if t == "p":
        posts = db.execute(f'select * from post ORDER BY created DESC limit {offset} Offset {from_row}').fetchall()
    if t == "favorites":
        posts = db.execute(f'select * from post where id in (select favorite_id from favorites limit {offset} Offset {from_row}) ORDER BY created DESC').fetchall()
        
    final = []
    for p in posts:
        final.append({'id':p["id"],"author_id":p["author_id"],"created":p["created"],"title":p["title"],"file_path":p["file_path"],"persons":p["persons"],"file_size":p["file_size"],"file_type":p["file_type"]})
    print("total new :: ",len(posts),len(final))
    return {'status':200,'from':from_row,'end':from_row + len(final), "posts":final}

@bp.route('/get_favorites', methods=('GET',))
@login_required
def get_favorites():
    db = get_db()
    res = []
    res = db.execute(
                f'Select * from favorites',
            ).fetchall()
    p = []
    for r in res:
        p.extend(db.execute(
                f'Select * from post where id={int(r["favorite_id"])}',
            ).fetchall())
    final = []
    for p in p:
        final.append({'id':p["id"],"author_id":p["author_id"],"created":p["created"],"title":p["title"],"file_path":p["file_path"],"persons":p["persons"],"file_size":p["file_size"],"file_type":p["file_type"]})
    
    return render_template('gallery/index.html', posts=final, base_url = request.base_url, is_favorites = True)


@bp.route('/reload-gallery', methods=('GET',))
@login_required
def reload_gallery():
    db = get_db()
    print("Reloading")
    if g.user is not None:
        url_regex = re.compile(r"^http[s]{0,1}:\/\/", re.IGNORECASE)
        
        files = os.listdir(path)
        try:
            with current_app.open_resource('schema.sql') as dbf:
                    db.executescript(dbf.read().decode('utf8'))
            for f in files:
                
                try:
                    ext = magic.from_file(path + f, mime=True)
                    ext = ext.split("/")[-1].lower()
                    _ext = f.split(".")[-1]
                    _ext = _ext if _ext.lower() in ["jpeg", "jpg", "mp4", "png", "gif", "tiff"] else "file"
                    print(f, ext)
                    if ext in ["jpeg", "jpg", "mp4", "png", "gif", "tiff"]:
                        db.execute(
                            'INSERT INTO post (created, title, file_path, author_id, file_size, file_type)'
                            ' VALUES (?, ?, ?, ?, ?, ?)',
                            (creation_date(path + f) ,f, f, g.user['id'], size(os.path.getsize(path + f),system=alternative), _ext.lower())
                        )
                except Exception as exp:
                    print("Error :: ",exp,f)
        except Exception as exp:
            print("Error :: ",exp,f)
        db.commit()
    return redirect(url_for('gallery.index'))

@bp.route('/randomize', methods=('GET', ))
@login_required
def randomize():
    if g.user is not None:
        db = get_db()
        posts = db.execute(
            'SELECT *'
            ' FROM post'
            ' ORDER BY created DESC'
        ).fetchall()
        print("Posts :: ",len(posts))
        random.shuffle(posts)
        final = []
        for p in posts:
            final.append({'id':p["id"],"author_id":p["author_id"],"created":p["created"],"title":p["title"],"file_path":p["file_path"],"persons":p["persons"],"file_size":p["file_size"],"file_type":p["file_type"]})
        
        return render_template('gallery/index.html', posts=final, base_url = request.base_url, is_favorites = False)
    return redirect(url_for("auth.login"))

@bp.route('/get_favorites/randomize', methods=('GET',))
@login_required
def favorites_randomize():
    if g.user is not None:
        db = get_db()
        f = db.execute(
            'SELECT *'
            ' FROM favorites'
        ).fetchall()
        print("Posts :: ",len(f))
        posts = []
        for r in f:
            posts.extend(db.execute(
                    f'Select * from post where id={int(r["favorite_id"])}',
                ).fetchall())
        random.shuffle(posts)
        final = []
        for p in posts:
            final.append({'id':p["id"],"author_id":p["author_id"],"created":p["created"],"title":p["title"],"file_path":p["file_path"],"persons":p["persons"],"file_size":p["file_size"],"file_type":p["file_type"]})
        
        return render_template('gallery/index.html', posts=final, base_url = request.base_url, is_favorites = True)
    return redirect(url_for("auth.login"))

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['file_path']
        error = None

        if not title:
            error = 'Title is required.'
        url_regex = re.compile(r"^(http[s]{0,1}:\/\/|data:)", re.IGNORECASE)
        if error is not None:
            flash(error)
        else:
            file_name = ""
            if url_regex.match(body) is not None:
                response = requests.head(body)
                headers = response.headers
                
                response = requests.get(body, stream=True)
                ext = ""
                if 'content-type' in headers:
                    _ext = headers['content-type'].split(";")
                    if len(_ext) > 0:
                        ext = _ext[0].split("/")[-1]
                if ext == "":
                    ext = body.split("/")[-1].split(".")[-1]
                if not ext.lower() in ["jpeg", "jpg", "mp4", "png", "gif", "tiff"]:
                    ext = 'file'
                if ext in ["jpeg", "jpg", "mp4", "png", "gif", "tiff"]:
                    while True:
                        file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 16)) + ("." if ext != 'file' else '') + ext
                        if not os.path.exists(path + file_name):
                            break
                    
                    with open(path + file_name, "wb") as handle:
                        for data in tqdm(response.iter_content()):
                            handle.write(data)
                    db = get_db()
                    db.execute(
                        'INSERT INTO post (created, title, file_path, author_id, file_size, file_type)'
                        ' VALUES (?, ?, ?, ?, ?, ?)',
                        (creation_date(path + file_name) , file_name, file_name, g.user['id'], size(os.path.getsize(path+file_name),system=alternative), ext.lower())
                    )
                    db.commit()
                    return redirect(url_for('gallery.index'))
                else:
                    flash("Not a image/video type.")
        return {}

    return render_template('gallery/create.html')

@bp.route('/<int:id>/<string:ptype>/get-post/', methods=('GET', 'POST'))
@login_required
def get_post(id, ptype):
    post = None
    print("Getting post :: id=",id,"ptype=",ptype)
    if ptype == "p":
        post = get_db().execute(
            'SELECT * '
            ' FROM post '
            ' WHERE id = ?',
            (id,)
        ).fetchone()
    
    if ptype == "favorites":
        post = get_db().execute(
            'SELECT * '
            ' FROM favorites '
            ' WHERE favorite_id = ?',
            (id,)
        ).fetchone()
    print("GoT POST :: ",post["id"])
    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    # if check_author and post['author_id'] != g.user['id']:
    #     abort(403)
    
    return {'id':post["id"],"author_id":post["author_id"],"created":post["created"],"title":post["title"],"file_path":post["file_path"],"persons":post["persons"],"file_size":post["file_size"],"file_type":post["file_type"]}

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id,"p")

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['file_path']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, file_path = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('gallery.index'))

    return render_template('gallery/update.html', post=post)

@bp.route('/<int:id>/<string:name>/delete/', methods=('GET','POST'))
@login_required
def delete(id,name):
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.execute('DELETE FROM favorites WHERE favorite_id = ?', (id,))
    db.commit()
    f = path + name
    try:
        os.remove(f)
    except:
        pass
    return {"status":200}