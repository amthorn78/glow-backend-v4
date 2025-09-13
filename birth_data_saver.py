"""
Transactional birth data saver following ChatGPT's debugging recommendations
"""
from datetime import date, time
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

def save_birth_data_transactional(db, BirthData, user_id, validated_data):
    """
    Save birth data with explicit transaction management and debugging
    Following ChatGPT's recommendations for database debugging
    """
    current_app.logger.info(f"[SAVE_DEBUG] Starting save for user {user_id}")
    current_app.logger.info(f"[SAVE_DEBUG] Validated data: {validated_data}")
    
    # 1) Load or create row
    birth_data = (
        db.session.query(BirthData).filter_by(user_id=user_id).one_or_none()
    )
    if birth_data is None:
        current_app.logger.info(f"[SAVE_DEBUG] Creating new BirthData record for user {user_id}")
        birth_data = BirthData(user_id=user_id)
        db.session.add(birth_data)
    else:
        current_app.logger.info(f"[SAVE_DEBUG] Updating existing BirthData record for user {user_id}")

    # 2) Assign typed values
    birth_data.birth_date = date(validated_data.year, validated_data.month, validated_data.day)
    birth_data.birth_time = time(validated_data.hour, validated_data.minute, 0)
    birth_data.birth_location = validated_data.location
    birth_data.latitude = validated_data.lat
    birth_data.longitude = validated_data.lng
    birth_data.timezone = validated_data.tz
    birth_data.data_consent = True
    
    current_app.logger.info(f"[SAVE_DEBUG] Assigned values:")
    current_app.logger.info(f"  birth_date: {birth_data.birth_date}")
    current_app.logger.info(f"  birth_time: {birth_data.birth_time}")
    current_app.logger.info(f"  birth_location: {birth_data.birth_location}")
    current_app.logger.info(f"  latitude: {birth_data.latitude}")
    current_app.logger.info(f"  longitude: {birth_data.longitude}")
    current_app.logger.info(f"  timezone: {birth_data.timezone}")

    try:
        # 3) Force SQL emission now
        current_app.logger.info("[SAVE_DEBUG] Flushing to database...")
        db.session.flush()
        current_app.logger.info("[SAVE_DEBUG] Flush successful")

        # 4) Prove row is persistent and refreshed from DB
        current_app.logger.info("[SAVE_DEBUG] Refreshing from database...")
        db.session.refresh(birth_data)
        current_app.logger.info("[SAVE_DEBUG] Refresh successful")

        # 5) Commit
        current_app.logger.info("[SAVE_DEBUG] Committing transaction...")
        db.session.commit()
        current_app.logger.info("[SAVE_DEBUG] Commit successful")
        
    except SQLAlchemyError as e:
        current_app.logger.error(f"[SAVE_DEBUG] Database error: {e}")
        db.session.rollback()
        current_app.logger.error("[SAVE_DEBUG] Transaction rolled back")
        raise

    # 6) Return exactly what's in DB, not a recomposed object
    result = {
        "user_id": user_id,
        "birth_date": birth_data.birth_date.isoformat() if birth_data.birth_date else None,
        "birth_time": birth_data.birth_time.isoformat() if birth_data.birth_time else None,
        "birth_location": birth_data.birth_location,
        "latitude": float(birth_data.latitude) if birth_data.latitude is not None else None,
        "longitude": float(birth_data.longitude) if birth_data.longitude is not None else None,
        "timezone": birth_data.timezone,
        "data_consent": birth_data.data_consent,
    }
    
    current_app.logger.info(f"[SAVE_DEBUG] Final result: {result}")
    return result

