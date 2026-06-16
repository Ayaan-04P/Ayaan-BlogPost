#---------- Flask and Related Modules ----------#
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user


#---------- SQLite Database Modules ----------#
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey


#---------- Security Modules Modules ----------#
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


#---------- Forms from form.py ----------#
from forms import CreatePostForm, RegistrationForm, LoginForm, CommentForm


#---------- datetime module ----------#
from datetime import date


#---------- Environment Variable Set-Up ----------#
from dotenv import load_dotenv
load_dotenv()
import os

#---------- Email and smtplib Set-Up ----------#
import smtplib
EMAIL = os.environ.get('EMAIL_KEY')
PASSWORD = os.environ.get('PASSWORD_KEY')

def send_email(name, email, phone, message): # Send email to the admin
    email_message = f"Subject:Query Regarding Blog\n\nName: {name}\nEmail: {email}\nPhone: {phone}\nMessage:{message}"
    with smtplib.SMTP("smtp.gmail.com", 587) as connection:
        connection.starttls()
        connection.login(user=EMAIL, password=PASSWORD)
        connection.sendmail(from_addr=email, to_addrs=EMAIL, msg=email_message)


#---------- Instructions for requirements.txt ----------#
'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''


#---------- Flask App Set-Up ----------#
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_KEY')


#---------- Bootstrap and CKEditor Integration ----------#
ckeditor = CKEditor(app)
Bootstrap5(app)


#---------- Admin-Only Decorator ----------#
def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if  (current_user.is_authenticated and current_user.id != 1) or (not current_user.is_authenticated):
            abort(403)
        return func(*args, **kwargs)
    return decorated_function


#---------- Login-Manager Set-Up ----------#
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


#---------- Create Database ----------#
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URL", "sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


#---------- Tables Configuration ----------#
class User(UserMixin, db.Model): # Table of users
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)

    #---------- RELATIONSHIP WITH BLOGPOST ----------#
    posts = relationship("BlogPost", back_populates="author")

    #---------- RELATIONSHIP WITH COMMENT ----------#
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model): # Table of posts
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    #---------- RELATIONSHIP WITH USER ----------#
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    #---------- RELATIONSHIP WITH COMMENT ----------#
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model): # Table of comments
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(800), nullable=False)

    # ---------- RELATIONSHIP WITH USER ----------#
    author_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    # ---------- RELATIONSHIP WITH BLOGPOST ----------#
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context(): # Add all the tables to database
    db.create_all()


#---------- Generation of picture for users in comment section ----------#
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


#---------- Routes Set-Up ----------#
@app.route('/register', methods=["GET", "POST"])
def register(): # Route for registration for user
    form = RegistrationForm()
    if form.validate_on_submit():

        email = form.email.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash("You have already signed up with that email, log in instead.")
            return redirect(url_for("login"))

        hash_salt_password = generate_password_hash(
            password=form.password.data,
            salt_length=8
        )

        user = User(
            email=email,
            password=hash_salt_password,
            name=form.name.data
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login(): # Route for log-in of user
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()

        if user is None:
            flash("That email does not exit, please try again.")
            return redirect(url_for("login"))

        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("get_all_posts"))

        else:
            flash("Incorrect password, please try again.")
            return redirect(url_for("login"))

    return render_template("login.html", form=form)


@app.route('/logout')
def logout(): # Route to log-out user
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts(): # Route to display all the posts
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id): # Route to display a specific post
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You are not logged in, please log in first.")
            return redirect(url_for("login"))
        new_comment = Comment(
            text=form.comment.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, form=form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post(): # Route to add a new post
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id): # Route to edit the post
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id): # Route to delete a post
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about(): # Route for "about me" page
    return render_template("about.html")


#---------- CONTACT PAGE SET-UP ----------#
@app.route("/contact", methods=["GET", "POST"])
def contact(): # Route for "contact me" page
    if request.method == "POST":
        data = request.form
        send_email(data["name"], data["email"], data["phone"], data["message"])
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


if __name__ == "__main__":
    app.run(debug=True)
