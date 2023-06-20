from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps


ADMIN_USER_ID = 1

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
app.app_context().push()
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
login_manager = LoginManager()
login_manager.init_app(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



# creaate admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != ADMIN_USER_ID:
            return abort(403)
        return f(*args, **kwargs)
    
    return decorated_function

        
##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    #author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = relationship('BlogPost', back_populates="user")
    comments = relationship("Comment", back_populates="user")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="comments")
    parent_post_id = db.Column(db.Integer, ForeignKey('blog_posts.id'))
    parent_post = relationship("BlogPost", back_populates="comments")

#db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["GET", "POST"])
def register():
    reg_form = RegisterForm()

    if reg_form.validate_on_submit():
        # check if email exists
        rec = User.query.filter_by(email=reg_form.email.data).first()
        if rec:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        
        # hash user password with 8 char salt
        pass_hash = generate_password_hash(reg_form.password.data, method='pbkdf2:sha256', salt_length=8)   
        new_user = User(name = reg_form.name.data, email = reg_form.email.data, password = pass_hash)
        db.session.add(new_user)
        db.session.commit()
        # auto login user 
        login_user(new_user)

        return redirect( url_for('get_all_posts') ) 
    
    return render_template("register.html", form=reg_form)


@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        in_email = login_form.email.data
        in_pass = login_form.password.data
        
        user = User.query.filter_by(email=in_email).first()
        if user:
            # check if database password matches what the user entered (in_pass)
            if check_password_hash(user.password, in_pass):
                login_user(user)
                return redirect( url_for('get_all_posts'))
            else:
                flash('Password incorrect, please try again.')
                return redirect( url_for('login') )
        else:
            flash("That email does not exist, please try again.")
            return redirect( url_for('login') )
        
    return render_template("login.html", form = login_form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comment_form = CommentForm()
    #comments = Comment.query.filter_by(parent_post_id=post_id).all()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect( url_for('show_post', post_id = post_id))
        
        new_comment = Comment()
        #new_comment.parent_post_id = post_id
        new_comment.parent_post = requested_post
        #new_comment.user_id = current_user.id
        new_comment.user = current_user
        new_comment.text = comment_form.comment.data
        db.session.add(new_comment)
        db.session.commit()
        comment_form.comment.data = ""
        #return redirect( url_for('show_post', post_id = post_id))
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            user=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        #author=post.author,
        #user = post.user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        #post.user = current_user,
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
