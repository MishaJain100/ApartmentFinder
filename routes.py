from flask import render_template, redirect, url_for, flash, request, jsonify, session, abort
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, date, time
from functools import wraps
from app import app, db
from models import User, PropertyListing, Appointment, Review, Payment, Neighbourhood, SavedListing
from utils import get_neighbourhood_data, generate_invoice
import json
from sqlalchemy import text

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['owner', 'admin']:
            flash('You need property owner privileges to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():    
    latest_listings = PropertyListing.query.filter_by(is_available=True).order_by(PropertyListing.created_at.desc()).limit(6).all()
    return render_template('index.html', listings=latest_listings)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        connection = db.engine.connect()
        result = connection.execute(
            text("""
                SELECT id, username, email, password_hash, role,
                       first_name, last_name, phone, created_at
                FROM app_user
                WHERE email = :email
            """),
            {"email": email}
        ).fetchone()
        connection.close()

        if result:
            user = User()
            user.id = result[0]
            user.username = result[1]
            user.email = result[2]
            user.password_hash = result[3]
            user.role = result[4]
            user.first_name = result[5]
            user.last_name = result[6]
            user.phone = result[7]
            user.created_at = result[8]

            if user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')

                if user.role == 'tenant':
                    return redirect(next_page or url_for('dashboard_tenant'))
                elif user.role == 'owner':
                    return redirect(next_page or url_for('dashboard_owner'))
                elif user.role == 'admin':
                    return redirect(next_page or url_for('admin_portal'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        with db.engine.begin() as connection:
            result = connection.execute(
                text("""
                    SELECT id FROM app_user 
                    WHERE username = :username OR email = :email
                """),
                {"username": username, "email": email}
            ).fetchone()

            if result:
                flash('Username or email already exists.', 'danger')
                return render_template('register.html')

            user = User()
            user.set_password(password)

            connection.execute(
                text("""
                    INSERT INTO app_user (
                        username, email, password_hash, role,
                        first_name, last_name, phone, created_at
                    ) VALUES (
                        :username, :email, :password_hash, :role,
                        :first_name, :last_name, :phone, CURRENT_TIMESTAMP
                    )
                """),
                {
                    "username": username,
                    "email": email,
                    "password_hash": user.password_hash,
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": phone
                }
            )

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard/tenant')
@login_required
def dashboard_tenant():
    if current_user.role != 'tenant':
        flash('Access denied. You need to be a tenant to view this page.', 'danger')
        return redirect(url_for('index'))
    
    
    saved = SavedListing.query.filter_by(user_id=current_user.id).all()
    saved_listings = [listing.property for listing in saved]
    
    
    appointments = Appointment.query.filter_by(tenant_id=current_user.id).order_by(Appointment.date.desc()).all()
    
    
    reviews = Review.query.filter_by(tenant_id=current_user.id).all()
    
    return render_template('dashboard_tenant.html', 
                           saved_listings=saved_listings, 
                           appointments=appointments, 
                           reviews=reviews)

@app.route('/dashboard/owner')
@login_required
@owner_required
def dashboard_owner():
    
    listings = PropertyListing.query.filter_by(owner_id=current_user.id).all()
    
    
    appointments = Appointment.query.join(PropertyListing).filter(
        PropertyListing.owner_id == current_user.id
    ).order_by(Appointment.date.desc()).all()
    
    
    metrics = {
        'total_properties': len(listings),
        'available_properties': sum(1 for listing in listings if listing.is_available),
        'total_appointments': len(appointments),
        'pending_appointments': sum(1 for appt in appointments if appt.status == 'pending'),
        'total_reviews': sum(len(listing.reviews) for listing in listings),
        'avg_rating': 0
    }
    
    
    all_reviews = []
    for listing in listings:
        all_reviews.extend(listing.reviews)
    
    if all_reviews:
        metrics['avg_rating'] = sum(review.rating for review in all_reviews) / len(all_reviews)
    
    return render_template('dashboard_owner.html', 
                           listings=listings, 
                           appointments=appointments, 
                           metrics=metrics)


@app.route('/properties')
def property_list():
    location = request.args.get('location', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    bedrooms = request.args.get('bedrooms', type=int)
    property_type = request.args.get('property_type', '')
    sort = request.args.get('sort', 'newest')
    
    query = PropertyListing.query.join(PropertyListing.neighbourhood).filter(PropertyListing.is_available == True)

    if location:
        query = query.filter(
            (PropertyListing.city.ilike(f'%{location}%')) |
            (PropertyListing.state.ilike(f'%{location}%')) |
            (PropertyListing.zip_code.ilike(f'%{location}%')) |
            (Neighbourhood.name.ilike(f'%{location}%'))
        )

    if min_price is not None:
        query = query.filter(PropertyListing.price >= min_price)

    if max_price is not None:
        query = query.filter(PropertyListing.price <= max_price)

    if bedrooms is not None:
        query = query.filter(PropertyListing.bedrooms >= bedrooms)

    if property_type:
        query = query.filter(PropertyListing.property_type == property_type)

    if sort == 'price_asc':
        query = query.order_by(PropertyListing.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(PropertyListing.price.desc())
    elif sort == 'bedrooms':
        query = query.order_by(PropertyListing.bedrooms.desc())
    else:
        query = query.order_by(PropertyListing.created_at.desc())

    listings = query.all()

    property_types = db.session.query(PropertyListing.property_type).distinct().all()
    property_types = [p[0] for p in property_types]

    return render_template('property_list.html', 
                          listings=listings, 
                          property_types=property_types,
                          filters={
                              'location': location,
                              'min_price': min_price,
                              'max_price': max_price,
                              'bedrooms': bedrooms,
                              'property_type': property_type
                          })

@app.route('/properties/<int:property_id>')
def property_detail(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    reviews = Review.query.filter_by(property_id=property_id).order_by(Review.created_at.desc()).all()
    
    
    avg_rating = 0
    if reviews:
        avg_rating = sum(review.rating for review in reviews) / len(reviews)
    
    
    is_saved = False
    if current_user.is_authenticated:
        saved = SavedListing.query.filter_by(user_id=current_user.id, property_id=property_id).first()
        is_saved = saved is not None
    
    
    neighbourhood = property_listing.neighbourhood
    
    return render_template(r'property_detail.html', 
                          property=property_listing, 
                          reviews=reviews, 
                          avg_rating=avg_rating,
                          is_saved=is_saved,
                          neighbourhood=neighbourhood)

@app.route('/properties/add', methods=['GET', 'POST'])
@login_required
@owner_required
def add_property():
    if request.method == 'POST':
        
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        bedrooms = int(request.form.get('bedrooms'))
        bathrooms = float(request.form.get('bathrooms'))
        area_sqft = float(request.form.get('area_sqft'))
        property_type = request.form.get('property_type')
        image_urls = request.form.get('image_urls')
        available_from = datetime.strptime(request.form.get('available_from'), '%Y-%m-%d').date()
        amenities = request.form.get('amenities')
        
        
        neighbourhood_name = request.form.get('neighbourhood')
        neighbourhood = Neighbourhood.query.filter_by(name=neighbourhood_name).first()
        
        if not neighbourhood:
            
            neighbourhood = Neighbourhood(
                name=neighbourhood_name,
                description=f"Information about {neighbourhood_name}",
                safety_rating=float(request.form.get('safety_rating', 3.0)),
                schools_rating=float(request.form.get('schools_rating', 3.0)),
                transportation_rating=float(request.form.get('transportation_rating', 3.0)),
                shopping_rating=float(request.form.get('shopping_rating', 3.0)),
                dining_rating=float(request.form.get('dining_rating', 3.0))
            )
            db.session.add(neighbourhood)
            db.session.commit()
        
        
        new_property = PropertyListing(
            title=title,
            description=description,
            price=price,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqft=area_sqft,
            property_type=property_type,
            image_urls=image_urls,
            is_available=True,
            available_from=available_from,
            amenities=amenities,
            owner_id=current_user.id,
            neighbourhood_id=neighbourhood.id
        )
        
        db.session.add(new_property)
        db.session.commit()
        
        flash('Property listing added successfully!', 'success')
        return redirect(url_for('property_detail', property_id=new_property.id))
    
    return render_template('add_property.html')

@app.route('/properties/edit/<int:property_id>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_property(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    
    if property_listing.owner_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to edit this property listing.', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))
    
    if request.method == 'POST':
        
        property_listing.title = request.form.get('title')
        property_listing.description = request.form.get('description')
        property_listing.price = float(request.form.get('price'))
        property_listing.address = request.form.get('address')
        property_listing.city = request.form.get('city')
        property_listing.state = request.form.get('state')
        property_listing.zip_code = request.form.get('zip_code')
        property_listing.bedrooms = int(request.form.get('bedrooms'))
        property_listing.bathrooms = float(request.form.get('bathrooms'))
        property_listing.area_sqft = float(request.form.get('area_sqft'))
        property_listing.property_type = request.form.get('property_type')
        property_listing.image_urls = request.form.get('image_urls')
        property_listing.is_available = 'is_available' in request.form
        property_listing.available_from = datetime.strptime(request.form.get('available_from'), '%Y-%m-%d').date()
        property_listing.amenities = request.form.get('amenities')
        property_listing.updated_at = datetime.utcnow()
        
        
        neighbourhood = property_listing.neighbourhood
        if neighbourhood:
            neighbourhood.safety_rating = float(request.form.get('safety_rating', neighbourhood.safety_rating))
            neighbourhood.schools_rating = float(request.form.get('schools_rating', neighbourhood.schools_rating))
            neighbourhood.transportation_rating = float(request.form.get('transportation_rating', neighbourhood.transportation_rating))
            neighbourhood.shopping_rating = float(request.form.get('shopping_rating', neighbourhood.shopping_rating))
            neighbourhood.dining_rating = float(request.form.get('dining_rating', neighbourhood.dining_rating))
        
        db.session.commit()
        
        flash('Property listing updated successfully!', 'success')
        return redirect(url_for('property_detail', property_id=property_id))
    
    return render_template('edit_property.html', property=property_listing)

@app.route('/properties/delete/<int:property_id>', methods=['POST'])
@login_required
@owner_required
def delete_property(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    if property_listing.owner_id != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to delete this property listing.', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))
    
    Appointment.query.filter_by(property_id=property_id).delete()
    Review.query.filter_by(property_id=property_id).delete()
    SavedListing.query.filter_by(property_id=property_id).delete()
    
    db.session.delete(property_listing)
    db.session.commit()
    
    flash('Property listing deleted successfully!', 'success')
    if current_user.role == 'admin':
        return redirect(url_for('admin_portal'))
    return redirect(url_for('dashboard_owner'))


@app.route('/appointments/schedule/<int:property_id>', methods=['GET', 'POST'])
@login_required
def schedule_appointment(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    
    if current_user.role != 'tenant':
        flash('Only tenants can schedule appointments.', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))
    
    if request.method == 'POST':
        
        appt_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        appt_time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        message = request.form.get('message')
        
        appointment_datetime = datetime.combine(appt_date, appt_time)
        
        appointment = Appointment(
            date=appt_date,
            time=appointment_datetime,
            message=message,
            property_id=property_id,
            tenant_id=current_user.id,
            status='pending'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        flash('Appointment scheduled successfully! The property owner will be notified.', 'success')
        return redirect(url_for('property_detail', property_id=property_id))
    
    return render_template('schedule_appointment.html', property=property_listing)

@app.route('/appointments/update/<int:appointment_id>', methods=['POST'])
@login_required
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    property_listing = PropertyListing.query.get(appointment.property_id)
    
    
    if not (current_user.id == property_listing.owner_id or current_user.id == appointment.tenant_id) and current_user.role != 'admin':
        flash('You do not have permission to update this appointment.', 'danger')
        return redirect(url_for('index'))
    
    status = request.form.get('status')
    if status in ['pending', 'confirmed', 'cancelled', 'completed']:
        appointment.status = status
        db.session.commit()
        flash('Appointment status updated successfully!', 'success')
    
    
    if current_user.role == 'owner':
        return redirect(url_for('dashboard_owner'))
    elif current_user.role == 'admin':
        return redirect(url_for('admin_portal'))
    else:
        return redirect(url_for('dashboard_tenant'))


@app.route('/reviews/add/<int:property_id>', methods=['POST'])
@login_required
def add_review(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    
    if current_user.role != 'tenant':
        flash('Only tenants can add reviews.', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))
    
    
    existing_review = Review.query.filter_by(
        property_id=property_id, 
        tenant_id=current_user.id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this property.', 'warning')
        return redirect(url_for('property_detail', property_id=property_id))
    
    
    rating = int(request.form.get('rating'))
    comment = request.form.get('comment')
    
    
    review = Review(
        rating=rating,
        comment=comment,
        property_id=property_id,
        tenant_id=current_user.id
    )
    
    db.session.add(review)
    db.session.commit()
    
    flash('Review added successfully!', 'success')
    return redirect(url_for('property_detail', property_id=property_id))


@app.route('/payment/<int:property_id>', methods=['GET', 'POST'])
@login_required
def payment_form(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    
    if current_user.role != 'tenant':
        flash('Only tenants can make payments.', 'danger')
        return redirect(url_for('property_detail', property_id=property_id))
    
    if request.method == 'POST':
        
        amount = float(request.form.get('amount'))
        payment_type = request.form.get('payment_type')
        
        
        payment = Payment(
            amount=amount,
            payment_type=payment_type,
            status='completed',  
            transaction_id=f'TRANS-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            user_id=current_user.id,
            property_id=property_id
        )
        
        db.session.add(payment)
        db.session.commit()
        
        flash('Payment processed successfully!', 'success')
        return redirect(url_for('dashboard_tenant'))
    
    return render_template('payment_form.html', property=property_listing)


@app.route('/saved/toggle/<int:property_id>', methods=['POST'])
@login_required
def toggle_saved_listing(property_id):
    property_listing = PropertyListing.query.get_or_404(property_id)
    
    
    saved = SavedListing.query.filter_by(
        user_id=current_user.id,
        property_id=property_id
    ).first()
    
    if saved:
        
        db.session.delete(saved)
        db.session.commit()
        flash('Property removed from saved listings.', 'info')
    else:
        
        saved_listing = SavedListing(
            user_id=current_user.id,
            property_id=property_id
        )
        db.session.add(saved_listing)
        db.session.commit()
        flash('Property added to saved listings.', 'success')
    
    return redirect(url_for('property_detail', property_id=property_id))

@app.route('/neighbourhood/<int:neighbourhood_id>')
def neighbourhood_info(neighbourhood_id):
    neighbourhood = Neighbourhood.query.get_or_404(neighbourhood_id)
    properties = PropertyListing.query.filter_by(neighbourhood_id=neighbourhood_id, is_available=True).all()
    
    return render_template('neighbourhood_info.html', 
                          neighbourhood=neighbourhood, 
                          properties=properties)

@app.route('/admin')
@login_required
@admin_required
def admin_portal():
    stats = {}

    with db.engine.connect() as connection:
        stats['users'] = connection.execute(
            text("SELECT COUNT(*) FROM app_user")
        ).scalar()

        stats['tenants'] = connection.execute(
            text("SELECT COUNT(*) FROM app_user WHERE role = 'tenant'")
        ).scalar()

        stats['owners'] = connection.execute(
            text("SELECT COUNT(*) FROM app_user WHERE role = 'owner'")
        ).scalar()

        stats['properties'] = connection.execute(
            text("SELECT COUNT(*) FROM property_listing")
        ).scalar()

        stats['appointments'] = connection.execute(
            text("SELECT COUNT(*) FROM appointment")
        ).scalar()

        stats['reviews'] = connection.execute(
            text("SELECT COUNT(*) FROM review")
        ).scalar()

        stats['neighbourhoods'] = connection.execute(
            text("SELECT COUNT(*) FROM neighbourhood")
        ).scalar()

        stats['payments'] = connection.execute(
            text("SELECT COUNT(*) FROM payment")
        ).scalar()

    return render_template('admin_portal.html', stats=stats)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    with db.engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, username, email, role, first_name, last_name, phone, created_at
                FROM app_user
                ORDER BY created_at DESC
            """)
        )
        users = [
            {
                "id": row[0],
                "username": row[1],
                "email": row[2],
                "role": row[3],
                "first_name": row[4],
                "last_name": row[5],
                "phone": row[6],
                "created_at": row[7]
            }
            for row in result.fetchall()
        ]

    return render_template('admin_users.html', users=users)

@app.route('/admin/properties')
@login_required
@admin_required
def admin_properties():
    with db.engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT p.id, p.owner_id, u.username AS owner_username, p.title, p.description, p.address,
                       p.city, p.state, p.zip_code, p.price, p.bedrooms,
                       p.bathrooms, p.area_sqft, p.property_type,
                       p.image_urls, p.is_available, p.available_from,
                       p.amenities, p.created_at, p.updated_at, p.neighbourhood_id
                FROM property_listing p
                JOIN app_user u ON p.owner_id = u.id
                ORDER BY p.created_at DESC
            """)
        )
        properties = [
            dict(zip(result.keys(), row))
            for row in result.fetchall()
        ]

    class AttrDict(dict):
        def __getattr__(self, key):
            return self[key] if key in self else None
        def __getitem__(self, key):
            return super().get(key)

    properties = [AttrDict({**p, 'owner': {'username': p.get('owner_username')}}) for p in properties]

    return render_template('admin_properties.html', properties=properties)

@app.route('/admin/appointments')
@login_required
@admin_required
def admin_appointments():
    with db.engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, "date", time, status, message,
                       created_at, property_id, tenant_id
                FROM appointment
                ORDER BY created_at DESC
            """)
        )
        rows = result.fetchall()
        keys = result.keys()
    
    appointments = [dict(zip(keys, row)) for row in rows]

    for appt in appointments:
        appt_obj = Appointment.query.get(appt['id'])
        appt['property'] = appt_obj.property
        appt['tenant'] = appt_obj.tenant
        appt['property'].owner = appt_obj.property.owner

    return render_template('admin_appointments.html', appointments=appointments)

@app.route('/admin/reviews')
@login_required
@admin_required
def admin_reviews():
    with db.engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, rating, "comment", created_at, 
                       property_id, tenant_id
                FROM review
                ORDER BY created_at DESC
            """)
        )
        rows = result.fetchall()
        keys = result.keys()

    reviews = [dict(zip(keys, row)) for row in rows]

    for review in reviews:
        review_obj = Review.query.get(review['id'])
        review['property'] = review_obj.property
        review['tenant'] = review_obj.tenant

    return render_template('admin_reviews.html', reviews=reviews)

@app.route('/admin/neighbourhoods', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_neighbourhoods():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        safety_rating = float(request.form.get('safety_rating', 0))
        schools_rating = float(request.form.get('schools_rating', 0))
        transportation_rating = float(request.form.get('transportation_rating', 0))
        shopping_rating = float(request.form.get('shopping_rating', 0))
        dining_rating = float(request.form.get('dining_rating', 0))

        with db.engine.begin() as conn:
            conn.execute(text("""
                UPDATE neighbourhood
                SET description = :description,
                    safety_rating = :safety_rating,
                    schools_rating = :schools_rating,
                    transportation_rating = :transportation_rating,
                    shopping_rating = :shopping_rating,
                    dining_rating = :dining_rating
                WHERE name = :name
            """), {
                'name': name,
                'description': description,
                'safety_rating': safety_rating,
                'schools_rating': schools_rating,
                'transportation_rating': transportation_rating,
                'shopping_rating': shopping_rating,
                'dining_rating': dining_rating
            })

        flash(f"Neighbourhood '{name}' updated successfully!", 'success')
        return redirect(url_for('admin_neighbourhoods'))

    with db.engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT id, name, description,
                       safety_rating, schools_rating, 
                       transportation_rating, shopping_rating, 
                       dining_rating
                FROM neighbourhood
                ORDER BY id DESC
            """)
        )

        class DummyNeighbourhood:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

            def get_overall_rating(self):
                return Neighbourhood.get_overall_rating(self)

        neighbourhoods = [
            DummyNeighbourhood(**dict(zip(result.keys(), row)))
            for row in result.fetchall()
        ]

    return render_template('admin_neighbourhoods.html', neighbourhoods=neighbourhoods)

@app.route('/admin/payments')
@login_required
@admin_required
def admin_payments():
    with db.engine.connect() as connection:
        result = connection.execute(text("""
            SELECT 
                p.id, p.amount, p.payment_type, p.status,
                p.transaction_id, p.created_at,
                p.user_id, p.property_id,
                pl.title AS property_title,
                u.first_name AS user_first_name,
                u.last_name AS user_last_name,
                u.email AS user_email,
                u.username AS username
            FROM payment p
            JOIN property_listing pl ON p.property_id = pl.id
            JOIN app_user u ON p.user_id = u.id
            ORDER BY p.created_at DESC
        """))

        class DummyUser:
            def __init__(self, first_name, last_name, email, username):
                self.first_name = first_name
                self.last_name = last_name
                self.email = email
                self.username = username

        class DummyProperty:
            def __init__(self, title):
                self.title = title

        class DummyPayment:
            def __init__(self, row):
                self.id = row.id
                self.amount = row.amount
                self.payment_type = row.payment_type
                self.status = row.status
                self.transaction_id = row.transaction_id
                self.created_at = row.created_at
                self.user_id = row.user_id
                self.property_id = row.property_id
                self.property_listing = DummyProperty(row.property_title)
                self.user = DummyUser(
                    row.user_first_name,
                    row.user_last_name,
                    row.user_email,
                    row.username
                )


        payments = [DummyPayment(row) for row in result.fetchall()]

    return render_template('admin_payments.html', payments=payments)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = db.session.execute(
        text("SELECT * FROM app_user WHERE id = :uid"), {'uid': user_id}
    ).fetchone()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))

    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.execute(text("DELETE FROM app_user WHERE id = :uid"), {'uid': user_id})
    db.session.commit()

    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_neighbourhood/<int:neighbourhood_id>', methods=['POST'])
@login_required
@admin_required
def delete_neighbourhood(neighbourhood_id):
    neighbourhood = db.session.execute(
        text("SELECT * FROM neighbourhood WHERE id = :nid"), {'nid': neighbourhood_id}
    ).fetchone()

    if not neighbourhood:
        flash('Neighbourhood not found.', 'danger')
        return redirect(url_for('admin_neighbourhoods'))

    db.session.execute(
        text("DELETE FROM neighbourhood WHERE id = :nid"), {'nid': neighbourhood_id}
    )
    db.session.commit()

    flash('Neighbourhood and associated properties deleted successfully!', 'success')
    return redirect(url_for('admin_neighbourhoods'))

@app.route('/admin/delete_review/delete/<int:review_id>', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    review = db.session.execute(
        text("SELECT * FROM review WHERE id = :rid"), {'rid': review_id}
    ).fetchone()

    if not review:
        flash('Review not found.', 'danger')
        return redirect(url_for('admin_reviews'))
    
    db.session.execute(
        text("DELETE FROM review WHERE id = :rid"), {'rid': review_id}
    )
    db.session.commit()

    flash('Review deleted successfully!', 'success')
    return redirect(url_for('admin_reviews'))

@app.route('/profile')
@login_required
def user_profile():
    return render_template('user_profile.html', user=current_user)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user = current_user
    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.phone = request.form.get('phone')
    
    password = request.form.get('password')
    if password and len(password) >= 6:
        user.set_password(password)
    
    db.session.commit()
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user_profile'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500
