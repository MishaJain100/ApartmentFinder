import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager

from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

admin_username = os.getenv("ADMIN_USERNAME")
admin_password = os.getenv("ADMIN_PASSWORD")
admin_email = os.getenv("ADMIN_EMAIL")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "temporary-dev-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"oracle+cx_oracle://{db_username}:{db_password}@localhost:1521/XE")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

with app.app_context():

    from models import User, PropertyListing, Appointment, Review, Payment, Neighbourhood, SavedListing
    
    db.create_all()
    existing_admin = User.query.filter_by(email=admin_email).first()

    if not existing_admin:
        admin_user = User(
            username=admin_username,
            email=admin_email,
            role="admin",
            first_name="Admin",
            last_name="User",
            phone="1234567890"
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()

    from routes import *