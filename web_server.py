#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Web Server for Telegram FileStore Bot
Runs on port 8000
"""

from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"ok": True, "service": "filestore-bot"})

def run_web_server():
    app.run(host="0.0.0.0", port=8000, debug=False)
    
