from datetime import datetime
import random
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

def get_neighbourhood_data(neighbourhood_name):
    safety_ratings = {
        "High": ["Safe neighbourhood with low crime rates", 4.5],
        "Medium": ["Average safety with moderate crime rates", 3.0],
        "Low": ["Exercise caution, higher crime rates", 1.5]
    }
    
    transport_options = {
        "Excellent": ["Multiple public transport options including subway, bus, and bike lanes", 4.5],
        "Good": ["Regular bus service and some bike lanes", 3.5],
        "Limited": ["Limited public transport options", 2.0],
        "Poor": ["Few public transport options, car recommended", 1.0]
    }
    
    amenities = {
        "Abundant": ["Many shopping centers, restaurants, and entertainment venues nearby", 4.5],
        "Moderate": ["Some shopping and dining options within walking distance", 3.0],
        "Sparse": ["Limited amenities, may need to travel for shopping and dining", 1.5]
    }
    
    school_ratings = {
        "Excellent": ["Top-rated schools in the area", 4.5],
        "Good": ["Above average schools nearby", 3.5],
        "Average": ["Schools with average ratings", 2.5],
        "Below Average": ["Schools with below average ratings", 1.5]
    }

    safety_key = random.choice(list(safety_ratings.keys()))
    transport_key = random.choice(list(transport_options.keys()))
    amenities_key = random.choice(list(amenities.keys()))
    school_key = random.choice(list(school_ratings.keys()))

    neighbourhood_data = {
        "name": neighbourhood_name,
        "safety": {
            "rating": safety_key,
            "description": safety_ratings[safety_key][0],
            "score": safety_ratings[safety_key][1]
        },
        "transportation": {
            "rating": transport_key,
            "description": transport_options[transport_key][0],
            "score": transport_options[transport_key][1]
        },
        "amenities": {
            "rating": amenities_key,
            "description": amenities[amenities_key][0],
            "score": amenities[amenities_key][1]
        },
        "schools": {
            "rating": school_key,
            "description": school_ratings[school_key][0],
            "score": school_ratings[school_key][1]
        },
        "overall_score": (safety_ratings[safety_key][1] + 
                          transport_options[transport_key][1] + 
                          amenities[amenities_key][1] + 
                          school_ratings[school_key][1]) / 4
    }
    
    return neighbourhood_data

def generate_invoice(payment):
    invoice = {
        "invoice_number": f"INV-{payment.id}-{datetime.now().strftime('%Y%m%d')}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tenant_name": f"{payment.user.first_name} {payment.user.last_name}",
        "tenant_email": payment.user.email,
        "property_address": payment.property_listing.address,
        "property_city": payment.property_listing.city,
        "property_state": payment.property_listing.state,
        "property_zip": payment.property_listing.zip_code,
        "payment_type": payment.payment_type,
        "amount": payment.amount,
        "transaction_id": payment.transaction_id,
        "status": payment.status
    }
    
    return invoice