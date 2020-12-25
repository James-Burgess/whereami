from os import getenv

from dotenv import load_dotenv, find_dotenv
from flask import Flask, g, request
from flask_httpauth import HTTPTokenAuth
from flask import render_template
from flask import Flask, Response, redirect, url_for, request, session, abort
from flask_login import LoginManager, UserMixin, \
                                login_required, login_user, logout_user
from tinydb import TinyDB, Query
from geopy.geocoders import Nominatim

from actions import process_spot

load_dotenv(find_dotenv())

app = Flask(__name__)
auth = HTTPTokenAuth(scheme='token')

# config
app.config.update(
    DEBUG = True,
    SECRET_KEY = getenv("SECRET_KEY", "unsafe")
)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    pass


@auth.verify_token
def verify_token(token):
    if token in tokens:
        return tokens[token]


@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if not (db_user := db.table('users').search(Query().email == email)):
        return

    user = User()
    user.id = email
    user.is_authenticated = request.form['password'] == db_user[0].get('password')

    return user


# callback to reload the user object
@login_manager.user_loader
def user_loader(email):
    if not (db_user := db.table('users').search(Query().email == email)):
        return

    user = User()
    user.id = email
    return user


# somewhere to login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'/>
                <input type='password' name='password' id='password' placeholder='password'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    email = request.form['email']
    if not (db_user := db.table('users').search(Query().email == email)):
        return "user not found"

    if request.form['password'] == db_user[0].get('password'):
        user = User()
        user.id = email
        login_user(user)
        return redirect(request.args.get("next") or '/')
    return 'Bad login'


# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return Response('<p>Logged out</p>')


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return Response('<p>Login failed</p>')


@app.route('/')
@login_required
def index():
    geolocator = Nominatim(user_agent="wheresjimmy")
    last_loc = db.table('locs').all()[-1]
    location = geolocator.reverse(f"{last_loc['lat']}, {last_loc['lng']}")
    key = getenv("HERE_API_KEY")
    return render_template('index.html', location=location.address, here_api_key=key, **last_loc)


@app.route('/spot', methods=['post'])
@auth.login_required
def spot():
    data = request.form.get('data')
    if data:
        db.table('loc').insert(process_spot(data))
        return f"processed!"
    return "Invalid request"

if __name__ == '__main__':
    db = TinyDB('db.json')
    app.run()
