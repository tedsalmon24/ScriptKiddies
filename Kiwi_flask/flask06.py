# FLASK Tutorial 1 -- We show the bare bones code to get an app up and running

# imports
import os  # os is used to get environment variables IP & PORT
from flask import Flask  # Flask is the web app that we will customize
from flask import render_template
from flask import request
from flask import redirect, url_for
from flask.templating import render_template_string
from database import db
from models import Note as Note
from models import User as User
from forms import RegisterForm
import bcrypt
from flask import session
from forms import LoginForm
from models import Comment as Comment
from forms import RegisterForm, LoginForm, CommentForm, SearchForm, UpdateAccountForm
from flask import *
from flask_login import current_user

# from flask_socketio import SocketIO, emit

app = Flask(__name__)  # create an app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flask_note_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'SE3155'
#  Bind SQLAlchemy db object to this Flask app
db.init_app(app)
# Setup models
with app.app_context():
    db.create_all()  # run under the app context


# @app.route is a decorator. It gives the function "index" special powers.
# In this case it makes it so anyone going to "your-url/" makes this function
# get called. What it returns is what is shown as the web page


@app.route('/search', methods=['POST'])
def search():
    form = SearchForm()
    posts = Note.query
    if form.validate_on_submit() and session.get('user'):
        Note.results = form.results.data
        posts = posts.filter(Note.text.like('%' + Note.results + '%'))
        posts = posts.order_by(Note.title).all()
        return render_template("search.html", form=form, results=Note.results, posts=posts, user=session['user'])


@app.route('/')
@app.route('/index')
def index():
    if session.get('user'):
        all_notes = db.session.query(Note).all()
        return render_template('index.html', notes=all_notes, user=session['user'])
    else:
        return redirect(url_for('register'))


@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)

@app.route('/notes/<note_id>/like')
def voteLike(note_id):
    if session.get('user'):
        my_note = db.session.query(Note).filter_by(id=note_id).one()
        my_note.score = 1
        db.session.add(my_note)
        return render_template("index.html", id=note_id, note=my_note)

@app.route('/notes/<note_id>/Dislike')
def voteDislike(score, note_id):
    if session.get('user'):
        my_note = db.session.query(Note).filter_by(note_score = score).one()
        my_note.score = 0
        db.session.add(my_note)
        return render_template("index.html", id=note_id, note=my_note)


@app.route('/notes/<note_id>/comment', methods=['POST'])
def new_comment(note_id):
    if session.get('user'):
        comment_form = CommentForm()
        # validate_on_submit only validates using POST
        if comment_form.validate_on_submit():
            # get comment data
            comment_text = request.form['comment']
            new_record = Comment(comment_text, int(note_id), session['user_id'])
            db.session.add(new_record)
            db.session.commit()

        return redirect(url_for('get_note', note_id=note_id))

    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    # check if a user is saved in session
    if session.get('user'):
        session.clear()

    return redirect(url_for('index'))


@app.route('/login', methods=['POST', 'GET'])
def login():
    login_form = LoginForm()
    # validate_on_submit only validates using POST
    if login_form.validate_on_submit():
        # we know user exists. We can use one()
        the_user = db.session.query(User).filter_by(email=request.form['email']).one()
        # user exists check password entered matches stored password
        if bcrypt.checkpw(request.form['password'].encode('utf-8'), the_user.password):
            # password match add user info to session
            session['user'] = the_user.first_name
            session['user_id'] = the_user.id
            # render view
            return redirect(url_for('get_notes'))

        # password check failed
        # set error message to alert user
        login_form.password.errors = ["Incorrect username or password."]
        return render_template("login.html", form=login_form)
    else:
        # form did not validate or GET request
        return render_template("login.html", form=login_form)


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()

    if request.method == 'POST' and form.validate_on_submit():
        # salt and hash password
        h_password = bcrypt.hashpw(
            request.form['password'].encode('utf-8'), bcrypt.gensalt())
        # get entered user data
        first_name = request.form['firstname']
        last_name = request.form['lastname']
        # create user model
        new_user = User(first_name, last_name, request.form['email'], h_password)
        # add user to database and commit
        db.session.add(new_user)
        db.session.commit()
        # save the user's name to the session
        session['user'] = first_name
        session['user_id'] = new_user.id  # access id value from user model of this newly added user
        # show user dashboard view
        return redirect(url_for('get_notes'))

    # something went wrong - display register view
    return render_template('register.html', form=form)


@app.route('/notes/delete/<note_id>', methods=['POST'])
def delete_note(note_id):
    # check if a user is saved in session
    if session.get('user'):
        # retrieve note from DB
        my_note = db.session.query(Note).filter_by(id=note_id).one()
        db.session.delete(my_note)
        db.session.commit()
        flash('You were successfully logged in')
    else:
        return redirect(url_for('login'))
    return redirect(url_for('get_notes'))


@app.route('/notes/edit/<note_id>', methods=['GET', 'POST'])
def update_note(note_id):
    # check if a user is saved in sessing
    if session.get('user'):
        if request.method == 'POST':
            # get title data
            title = request.form['title']
            # get note data
            text = request.form['noteText']
            note = db.session.query(Note).filter_by(id=note_id).one()
            # update note data
            note.title = title
            note.text = text
            # update note in DB
            db.session.add(note)
            db.session.commit()

            return redirect(url_for('get_notes'))
        else:
            # GET request - show new note form to edit note
            # retreieve user from database
            # retrieve note from databasee
            my_note = db.session.query(Note).filter_by(id=note_id).one()

        return render_template('new.html', note=my_note, user=session['user'])
    else:
        return redirect(url_for('login'))


@app.route('/notes/new', methods=['GET', 'POST'])
def new_note():
    # check if a user is saved in sessing
    if session.get('user'):
        # check method used for request
        if request.method == 'POST':
            # get title data
            title = request.form['title']
            # get note data
            text = request.form['noteText']
            # create date stamp
            from datetime import date
            today = date.today()
            # format date mm/dd/yyyy
            today = today.strftime("%m-%d-%Y")
            new_record = Note(title, text, today, session['user'], votes=0, score=0)
            db.session.add(new_record)
            db.session.commit()
            return redirect(url_for('get_notes'))
        else:
            # GET request - show new note form
            # retrieve user from database

            return render_template('new.html', user=session['user'])
    else:
        return redirect(url_for('login'))


@app.route('/notes/<note_id>')
def get_note(note_id):
    if session.get('user'):
        my_notes = db.session.query(Note).filter_by(id=note_id).one()
        form = CommentForm()
        return render_template('note.html', note=my_notes, user=session['user'], form=form)
    else:
        return redirect(url_for('login'))


# notes page
@app.route('/notes')
def get_notes():
    if session.get('user'):
        my_notes = db.session.query(Note).filter_by(user_id=session['user']).all()
        return render_template('notes.html', notes=my_notes, user=session['user'])
    else:
        return redirect(url_for('login'))


# retrieve account
@app.route('/accounts/<user_id>')
def get_account(user_id):
    if session.get('user'):
        my_account = db.session.query(User).filter_by(id=user_id).one()

        return render_template('note.html', usr=my_account, user=session['user'])
    else:
        return redirect(url_for('login'))


# accounts page
@app.route('/accounts')
def get_accounts():
    if session.get('user'):
        my_account = db.session.query(User).filter_by(id=session['user_id']).first()
        return render_template('accounts.html', fname=my_account.first_name,
                               lname=my_account.last_name, user=session['user'])
    else:
        return redirect(url_for('login'))


# update accounts page
@app.route('/accounts/edit/update_account', methods=['GET', 'POST'])
def update_account():
    form = UpdateAccountForm()
    my_account = db.session.query(User).filter_by(id=session['user_id']).first()
    if request.method == 'POST':
        updated_info = db.session.query(User).filter_by(id=session['user_id']).one()
        updated_info.first_name = form.firstname.data
        updated_info.last_name = form.lastname.data
        db.session.commit()
        return redirect(url_for('get_accounts'))
    return render_template('update_account.html', form=form, fname=my_account.first_name,
                           lname=my_account.last_name)


app.run(host=os.getenv('IP', '127.0.0.1'), port=int(os.getenv('PORT', 5000)), debug=True)

# To see the web page in your web browser, go to the url,
#   http://127.0.0.1:5000

# Note that we are running with "debug=True", so if you make changes and save it
# the server will automatically update. This is great for development but is a
# security risk for production.
