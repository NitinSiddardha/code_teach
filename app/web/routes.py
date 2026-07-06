import os
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv

load_dotenv()

from app.agent.teacher_agent import start_session, submit_code, send_signal, end_current_session


def create_app():
    app = Flask(__name__, template_folder="../../templates", static_folder="../../static")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/session/start")
    def session_start():
        payload = request.get_json(silent=True) or {}
        topic = payload.get("topic", "Python Variables")
        level = payload.get("level", "beginner")
        try:
            response = start_session(topic, level)
        except Exception as exc:
            return jsonify({"error": str(exc), "message": "Session start failed."}), 500
        return jsonify(response.model_dump() if hasattr(response, "model_dump") else response)

    @app.post("/api/session/assessment")
    def session_assessment():
        payload = request.get_json(silent=True) or {}
        topic = payload.get("topic", "Python Variables")
        level = payload.get("level", "beginner")
        conversation = payload.get("conversation", "")
        try:
            from app.chains.planner_chain import run_assessment
            quiz = run_assessment(topic, level, conversation)
        except Exception as exc:
            return jsonify({"error": str(exc), "message": "Assessment generation failed."}), 500
        return jsonify(quiz.model_dump() if hasattr(quiz, "model_dump") else quiz)

    @app.post("/api/session/submit")
    def session_submit():
        payload = request.get_json(silent=True) or {}
        code = payload.get("code", "")
        try:
            response = submit_code(code)
        except Exception as exc:
            return jsonify({"error": str(exc), "message": "Submission failed."}), 500
        return jsonify(response.model_dump() if hasattr(response, "model_dump") else response)

    @app.post("/api/session/signal")
    def session_signal():
        payload = request.get_json(silent=True) or {}
        signal = payload.get("signal")
        detail = payload.get("detail")
        try:
            response = send_signal(signal, detail)
        except Exception as exc:
            return jsonify({"error": str(exc), "message": "Signal handling failed."}), 500
        return jsonify(response.model_dump() if hasattr(response, "model_dump") else response)

    @app.post("/api/session/end")
    def session_end():
        try:
            summary = end_current_session()
        except Exception as exc:
            return jsonify({"error": str(exc), "message": "Ending session failed."}), 500
        return jsonify(summary.model_dump() if hasattr(summary, "model_dump") else summary)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()
