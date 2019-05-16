import os
from flask import render_template, flash, redirect, url_for, request,\
     abort, send_file, jsonify, make_response
from app import app, db
from app.forms import LoginForm
from app.models import User, NginxUploadFile, SharedFile
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
from app.forms import RegistrationForm, FileLifeTime
from config import UPLOAD_FOLDER, KEY_LENGTH, NGINX_UPLOAD_MODULE_ENABLED
from datetime import datetime, timedelta
from flask_babel import gettext as _

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['KEY_LENGTH'] = KEY_LENGTH
app.config['NGINX_UPLOAD_MODULE_ENABLED'] = NGINX_UPLOAD_MODULE_ENABLED

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])





@app.route('/')
def red():
    return redirect(url_for('upload_file'))

@app.route('/upload',  methods=['GET', 'POST'])
@login_required
def upload_file():
    form = FileLifeTime()
    if request.headers.getlist("X-Forwarded-For"):
        remote_ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        remote_ip = request.environ.get('REMOTE_ADDR', None)
    upload_file = None
    if app.config['NGINX_UPLOAD_MODULE_ENABLED']:
        if 'myfile.name' in request.form and 'myfile.path' in request.form:
            realpath = os.path.realpath(request.form['myfile.path'])
            storepath = app.config['NGINX_UPLOAD_MODULE_STORE']
            storepath = os.path.realpath(storepath)

            if realpath.startswith(storepath):
                upload_file = NginxUploadFile(
                    filename=request.form['myfile.name'],
                    path=request.form['myfile.path']
                )
    else:
        if 'myfile' in request.files and request.files['myfile']:
            upload_file = request.files['myfile']
            days = form.lifetime_days.data
            hours = form.lifetime_hours.data
            mins = form.lifetime_minutes.data
            seconds = form.lifetime_seconds.data
            global expire_date
            expire_date = datetime.today() + timedelta(days=days, hours=hours, minutes=mins, seconds=seconds)





    if upload_file is None:
        message = _("The file is required.")
        if request.is_xhr:
            return jsonify(message=message), 400
        else:
            return render_template('index.html', error=message, form=form)

    shared_file = SharedFile()
    shared_file.upload_file = upload_file
    shared_file.remote_ip = remote_ip
    shared_file.expire_date = expire_date
    shared_file.save()
    if request.is_xhr:
        return jsonify(url=url_for('show_uploaded_file', key=shared_file.key,
                                   secret=shared_file.delete_key))
    else:
        return redirect(url_for('show_uploaded_file', key=shared_file.key,
                                secret=shared_file.delete_key))




@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('upload_file'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('upload_file')
        return redirect(next_page)
    return render_template('login.html',  title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('upload_file'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('upload_file'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration is complete!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/uploaded/<key>/<secret>/')
def show_uploaded_file(key, secret):
    shared_file = SharedFile.get_or_404(key)

    if secret != shared_file.delete_key:
        abort(404)

    return render_template('show_uploaded_file.html', f=shared_file)


@app.route('/get/<key>/')
def show_get_file(key):
    if expire_date > datetime.now():
        shared_file = SharedFile.get_or_404(key)
        return render_template('show_get_file.html', f=shared_file)
    elif expire_date <= datetime.now():
        return render_template('404.html')



@app.route('/get/<key>/<filename>')
def get_file(key, filename):

    if expire_date > datetime.now():
        shared_file = SharedFile.get_or_404(key)

        if not shared_file.filename == filename:
            abort(404)

        filepath = os.path.join(app.config['UPLOAD_FOLDER'],
                                shared_file.path, filename)
        if not os.path.isfile(filepath):
            abort(404)


        filesize = str(shared_file.size)
        response = make_response(send_file(filepath, as_attachment=True,
                                attachment_filename=filename))
        response.headers['Content-Length'] = filesize

        return response
    else:
        return render_template('404.html')


@app.route('/delete/<key>/<secret>/', methods=['GET', 'POST'])
def show_delete_file(key, secret):
    shared_file = SharedFile.get_or_404(key)

    if secret != shared_file.delete_key:
        abort(404)

    if request.method == 'POST':
        shared_file.delete()
        flash(_('Your file have been deleted.'))
        return redirect(url_for('show_upload_form'))

    return render_template('show_delete_file.html', f=shared_file)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS