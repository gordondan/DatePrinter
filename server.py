from flask import Flask, jsonify, request, Response, send_from_directory
import subprocess
import sys
import os
import html
import re
from datetime import datetime


app = Flask(__name__)


@app.route("/api/pi-label/options", methods=["GET"])
def get_pi_label_options():
    """
    Return the available CLI options for pi-label-printer.py as JSON.
    This mirrors the argparse flags defined in pi-label-printer.py.
    """
    options = [
        {
            "flag": "-l",
            "long_flag": "--list",
            "type": "bool",
            "default": False,
            "description": "Force printer selection menu (ignore default printer)",
        },
        {
            "flag": "-c",
            "long_flag": "--count",
            "type": "int",
            "default": 1,
            "description": "Number of labels to print",
        },
        {
            "flag": "-d",
            "long_flag": "--date",
            "type": "string",
            "format": "YYYY-MM-DD",
            "description": "Specific date to print (default: today)",
        },
        {
            "flag": "-m",
            "long_flag": "--message",
            "type": "string",
            "description": "Custom message to print in center of label",
        },
        {
            "flag": "-b",
            "long_flag": "--border-message",
            "type": "string",
            "description": "Custom border message for top and bottom borders",
        },
        {
            "flag": "-s",
            "long_flag": "--side-border",
            "type": "string",
            "description": "Custom side border message (left/right, rotated)",
        },
        {
            "flag": "-i",
            "long_flag": "--image",
            "type": "string",
            "description": "Path to PNG image to include (cropped to fit)",
        },
        {
            "flag": "-o",
            "long_flag": "--show-date",
            "type": "bool",
            "default": False,
            "description": "Show dates on the label (hidden by default)",
        },
        {
            "flag": "-p",
            "long_flag": "--preview-only",
            "type": "bool",
            "default": False,
            "description": "Generate label image only (do not print)",
        },
    ]

    return jsonify({
        "script": "pi-label-printer.py",
        "endpoint": "/app/pi-label/options",
        "options": options,
    })


@app.route("/app/pi-label", methods=["GET"])
def pi_label_form():
    """Serve the HTML UI (now also available at /app via index.html)."""
    return send_from_directory(os.path.join(os.path.dirname(__file__), "www"), "index.html")


def build_command_from_payload(payload: dict):
    """Build command list for pi-label-printer.py based on provided payload."""
    script_path = os.path.join(os.path.dirname(__file__), 'pi-label-printer.py')
    cmd = [sys.executable or 'python3', script_path]

    # Booleans
    if payload.get('list') is True:
        cmd.append('-l')
    if payload.get('show_date') is True:
        cmd.append('-o')
    if payload.get('preview_only') is True:
        cmd.append('-p')

    # Integers
    count = payload.get('count')
    if count is not None:
        try:
            count_val = int(count)
            if count_val > 0:
                cmd.extend(['-c', str(count_val)])
        except (TypeError, ValueError):
            pass

    # Strings
    mapping = [
        ('date', '-d'),
        ('message', '-m'),
        ('border_message', '-b'),
        ('side_border', '-s'),
        ('image', '-i'),
    ]
    for key, flag in mapping:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            cmd.extend([flag, val.strip()])

    return cmd


def validate_payload(payload: dict):
    """Validate incoming POST data. Returns (ok: bool, errors: list[str])."""
    errors = []

    # count: positive integer if provided
    if 'count' in payload and payload['count'] is not None:
        try:
            count_val = int(payload['count'])
            if count_val <= 0:
                errors.append("'count' must be a positive integer")
        except (TypeError, ValueError):
            errors.append("'count' must be an integer")

    # date: YYYY-MM-DD if provided
    date_val = payload.get('date')
    if date_val:
        if not isinstance(date_val, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_val):
            errors.append("'date' must be in YYYY-MM-DD format")
        else:
            try:
                datetime.strptime(date_val, "%Y-%m-%d")
            except ValueError:
                errors.append("'date' is not a valid calendar date")

    # image: must exist if provided
    img = payload.get('image')
    if img:
        if not isinstance(img, str) or not os.path.isfile(img):
            errors.append("'image' path does not exist on server")

    return (len(errors) == 0, errors)


@app.route('/api/pi-label/print', methods=['POST'])
def post_pi_label_print():
    """Trigger printing via pi-label-printer.py with provided options (JSON body)."""
    data = request.get_json(silent=True) or {}

    # Validate payload
    ok, errors = validate_payload(data)
    if not ok:
        return jsonify({'errors': errors}), 400

    cmd = build_command_from_payload(data)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        response = {
            'command': cmd,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }
        status = 200 if result.returncode == 0 else 500
        return jsonify(response), status
    except FileNotFoundError:
        return jsonify({'error': 'pi-label-printer.py not found', 'command': cmd}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/app', methods=['GET'])
@app.route('/app/', methods=['GET'])
def app_index():
    """Serve the index HTML that includes the print form and links."""
    return send_from_directory(os.path.join(os.path.dirname(__file__), "www"), "index.html")


@app.route('/app/date', methods=['GET'])
def app_date_print():
    """Run pi-label-printer.py with default options (today's date) and show result."""
    script_path = os.path.join(os.path.dirname(__file__), 'pi-label-printer.py')
    cmd = [sys.executable or 'python3', script_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        ok = result.returncode == 0
        status = 'OK' if ok else 'Error'
        color = '#0a7d29' if ok else '#b00020'
        body = f"""
        <!doctype html>
        <meta charset='utf-8' />
        <title>Pi Label Printer — /app/date</title>
        <style>
          body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, sans-serif; margin: 24px; }}
          .status {{ color: {color}; font-weight: 600; }}
          pre {{ background: #f6f8fa; padding: 12px; border-radius: 6px; }}
          a {{ color: #0366d6; text-decoration: none; }}
        </style>
        <h1>Print Today's Date</h1>
        <div class='status'>{status}: ran pi-label-printer.py</div>
        <h2>Command</h2>
        <pre>{html.escape(' '.join(cmd))}</pre>
        <h2>stdout</h2>
        <pre>{html.escape(result.stdout)}</pre>
        <h2>stderr</h2>
        <pre>{html.escape(result.stderr)}</pre>
        <p><a href='/app'>Back to index</a></p>
        """
        return Response(body, mimetype='text/html'), (200 if ok else 500)
    except FileNotFoundError:
        return Response("pi-label-printer.py not found", mimetype='text/plain'), 500
    except Exception as e:
        return Response(str(e), mimetype='text/plain'), 500


if __name__ == "__main__":
    # Simple dev server for local testing
    app.run(host="0.0.0.0", port=5000, debug=False)
