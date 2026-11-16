"""Authentication REST API for token issuance and session inspection."""

import os
from flask import Blueprint, jsonify, request

from security import generate_token, get_current_user, rate_limit, require_auth

auth_blueprint = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_blueprint.route("/token", methods=["POST"])
@rate_limit(scope="auth")
def issue_token():
    """
    Public authentication endpoint to obtain a standard HS256 Bearer JWT.
    Accepts user identification and credentials, returning a signed token.
    """
    data = request.get_json(force=True) or {}
    user_id = (data.get("user_id") or data.get("username") or "").strip()
    role = (data.get("role") or "user").strip().lower()

    if not user_id:
        return jsonify({"success": False, "error": "user_id or username is required."}), 400

    # Role protection: admin role in production requires configured admin secret
    if role == "admin":
        admin_secret = os.getenv("ADMIN_AUTH_SECRET")
        provided_secret = data.get("admin_secret") or data.get("password")
        if admin_secret and provided_secret != admin_secret:
            return jsonify({"success": False, "error": "Invalid administrative credentials."}), 403

    token_ttl = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))
    token = generate_token(user_id=user_id, role=role, expires_in=token_ttl)

    return jsonify({
        "success": True,
        "token": token,
        "token_type": "Bearer",
        "expires_in": token_ttl,
        "user": {
            "user_id": user_id,
            "role": role,
        },
    }), 200


@auth_blueprint.route("/me", methods=["GET"])
@require_auth()
def get_authenticated_user():
    """Returns metadata for the currently authenticated user session."""
    user = get_current_user()
    return jsonify({
        "success": True,
        "user": user,
    }), 200

