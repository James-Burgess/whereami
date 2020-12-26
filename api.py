from os import getenv
import json

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
    if getenv("SERVER_KEY", 'unsafe') == token:
        return "internal server"


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
        return render_template('login.html')
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
    try:
        last_loc = db.table('locs').all()[-1]
    except IndexError:
        last_loc = {"lat": 35.1592248, "lng": -98.451035, "time": "no data"}
    location = geolocator.reverse(f"{last_loc['lat']}, {last_loc['lng']}")
    key = getenv("HERE_API_KEY")
    return render_template('index.html', location=location.address, here_api_key=key, **last_loc)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if request.method == 'GET':
        if request.args.get("secret", "none") == getenv("ADMIN_PASS"):
                return f'''
                       <form action='admin' method='POST'>
                        <input type='text' name='email' id='email' placeholder='email'/>
                        <input type='password' name='password' id='password' placeholder='password'/>
                        <input type='secret' name='secret' id='secret' placeholder='secret'/>
                        <input type='submit' name='submit'/>
                       </form>
                       '''
    elif request.method == 'POST':
        if request.form['secret'] == getenv("ADMIN_PASS"):
            db.table('users').insert({"email": request.form["email"], "password": request.form['password']})
            return "succ"

    return "You are not allowed here"



@app.route('/spot', methods=['post'])
@auth.login_required
def spot():
    data = request.form.get('data')
    if data:
        db.table('locs').insert(process_spot(data))
        return f"processed!"
    return "Invalid request"

if __name__ == '__main__':
    db = TinyDB('./db/db.json')

    if admin := getenv("ADMIN_USER"):
        if not db.table('users').search(Query().email == admin):
            db.table('users').insert({"email": admin, "password": getenv("ADMIN_PASS")})
    app.run(host='0.0.0.0', port=8080)
