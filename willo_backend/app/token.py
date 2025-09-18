import jwt
import dotenv

def generate_token(form_id):
    payload = {
        "form_id": form_id
    }
    token = jwt.encode(payload, dotenv.get_key("SECRET_KEY"), algorithm="HS256")
    return token

def is_authorized(token, form_id):
    try:
        payload = jwt.decode(token, dotenv.get_key("SECRET_KEY"), algorithms=["HS256"])
        return payload.get("form_id") == form_id
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False