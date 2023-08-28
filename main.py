from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
# Terminal: pip3 install -U Flask-SQLAlchemy
from flask_bootstrap import Bootstrap
# Terminal: pip3 install flask-bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, Length, DataRequired
# Terminal: pip3 install flask-login
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import spoonacular as sp
import creds

api = sp.API(creds.MY_API_KEY)

app = Flask(__name__)
app.config["SECRET_KEY"] = "Shhhthisisasecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///user-info.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.app_context().push()
Bootstrap(app)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(20))
    recipes = db.relationship("Recipe", backref="user")


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_name = db.Column(db.String(100))
    recipe_link = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    recipe_note = db.Column(db.String(500))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db.create_all()


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=20)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8, max=80)])


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=3, max=20)])
    email = StringField("Email", validators=[DataRequired(), Email(message="Invalid Email"), Length(max=40)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8, max=80)])


class NoteForm(FlaskForm):
    note = StringField("Note", validators=[InputRequired(), Length(min=3, max=500)])


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    form.validate_on_submit()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method="sha256")
        user = User.query.filter_by(username=form.username.data).first()
        email = User.query.filter_by(email=form.email.data).first()
        if email:
            return render_template("email_taken.html")
        elif user:
            return render_template("username_taken.html")
        else:
            new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            return render_template('successful_new_user.html')
    return render_template('sign_up.html', form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
        return render_template('invalid_warning.html')
    return render_template('log_in.html', form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/dietsandintolerances")
def diets_intolerances():
    return render_template('diets_and_intolerances.html')


@app.route("/randomrecipe")
def random_recipe():
    response = api.get_random_recipes()
    data = response.json()
    title = data["recipes"][0]["title"]
    preparation = data["recipes"][0]["readyInMinutes"]
    servings = data["recipes"][0]["servings"]
    diets = data["recipes"][0]["diets"]
    link = data["recipes"][0]["spoonacularSourceUrl"]
    dishes = data["recipes"][0]["dishTypes"]
    note = "Write down something if you need to."

    add_new_recipe = Recipe(recipe_name=title, recipe_link=link, user_id=current_user.id, recipe_note=note)
    db.session.add(add_new_recipe)
    db.session.commit()

    return render_template('random_recipe.html', title=title,
                           preparation=preparation,
                           servings=servings,
                           diets=diets,
                           link=link,
                           dishes=dishes)


@app.route("/myrecipes")
def my_recipes():
    all_recipe_data = Recipe.query.filter(Recipe.user_id == current_user.id).all()
    return render_template('my_recipes.html', all_recipe_data=all_recipe_data)


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete(id):
    recipe_to_delete = Recipe.query.get(id)
    db.session.delete(recipe_to_delete)
    db.session.commit()
    return redirect(url_for('my_recipes'))


@app.route("/update/<int:id>", methods=["GET", "POST"])
def update(id):
    form = NoteForm()
    note_to_update = Recipe.query.get(id)
    name = note_to_update.recipe_name
    if request.method == "POST":
        note_to_update.recipe_note = request.form["note"]
        db.session.commit()
    return render_template('my_note.html', form=form, note_to_update=note_to_update, name=name)


@app.route("/trivia")
def trivia():
    response = api.get_random_food_trivia()
    data = response.json()
    random_trivia = data["text"]
    return render_template("food_trivia.html", trivia=random_trivia)


if __name__ == "__main__":
    app.run(debug=True, port=8000)
