from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from sqlalchemy import Sequence

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'app_user'
    
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    properties = db.relationship('PropertyListing', backref='owner', lazy=True)
    appointments_tenant = db.relationship('Appointment', backref='tenant', lazy=True, foreign_keys='Appointment.tenant_id')
    reviews = db.relationship('Review', backref='tenant', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    saved_listings = db.relationship('SavedListing', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PropertyListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Float, nullable=False)
    area_sqft = db.Column(db.Float, nullable=False)
    property_type = db.Column(db.String(50), nullable=False)  
    image_urls = db.Column(db.Text)  
    is_available = db.Column(db.Boolean, default=True)
    available_from = db.Column(db.Date, nullable=False)
    amenities = db.Column(db.Text)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    neighbourhood_id = db.Column(db.Integer, db.ForeignKey('neighbourhood.id'))
    
    appointments = db.relationship('Appointment', backref='property', lazy=True)
    reviews = db.relationship('Review', backref='property', lazy=True)
    saved_by = db.relationship('SavedListing', backref='property', lazy=True)
    
    def get_image_list(self):
        if not self.image_urls:
            return []
        return self.image_urls.split(',')
    
    def get_amenities_list(self):
        if not self.amenities:
            return []
        return self.amenities.split(',')

class Neighbourhood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    safety_rating = db.Column(db.Float)  
    schools_rating = db.Column(db.Float)  
    transportation_rating = db.Column(db.Float)  
    shopping_rating = db.Column(db.Float)  
    dining_rating = db.Column(db.Float)  
    
    properties = db.relationship('PropertyListing', backref='neighbourhood', lazy=True)
    
    def get_overall_rating(self):
        ratings = [self.safety_rating, self.schools_rating, 
                  self.transportation_rating, self.shopping_rating, 
                  self.dining_rating]
        valid_ratings = [r for r in ratings if r is not None]
        if not valid_ratings:
            return 0
        return sum(valid_ratings) / len(valid_ratings)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    property_id = db.Column(db.Integer, db.ForeignKey('property_listing.id', name='fk_appointment_property_id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    property_id = db.Column(db.Integer, db.ForeignKey('property_listing.id', name='fk_review_property_id'), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)  
    status = db.Column(db.String(20), default='pending')  
    transaction_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property_listing.id', name='fk_payment_property_id'), nullable=False)
    
    property_listing = db.relationship('PropertyListing')

class SavedListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property_listing.id', name='fk_listing_property_id'), nullable=False)
