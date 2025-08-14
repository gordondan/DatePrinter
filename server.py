from flask import Flask, jsonify, request, Response
import subprocess
import sys
import os
import html
import re
from datetime import datetime


app = Flask(__name__)


@app.route("/app/pi-label/options", methods=["GET"])
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
    """Simple HTML form to submit options to the POST endpoint."""
    return Response(
        """
        <!doctype html>
        <meta charset="utf-8" />
        <title>Pi Label Printer</title>
        <style>
          :root { --ok:#0a7d29; --err:#b00020; --muted:#555; --bg:#f6f8fa; }
          body { font-family: system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif; margin: 24px; }
          h1 { margin: 0 0 8px; }
          .muted { color: var(--muted); margin-bottom: 18px; }
          label { display: block; margin: 8px 0 4px; }
          input[type=text], input[type=number], input[type=date] { width: 360px; padding: 8px; }
          .row { margin-bottom: 12px; }
          button { padding: 10px 14px; }
          pre { background: var(--bg); padding: 12px; border-radius: 6px; overflow: auto; max-width: 900px; }
          .status { margin-top: 12px; font-weight: 600; }
          .ok { color: var(--ok); }
          .err { color: var(--err); }
        </style>
        <h1>Pi Label Printer</h1>
        <div class="muted">Submit options to run pi-label-printer.py on the server.</div>
        <form id="labelForm">
          <div class="row"><label>Count</label><input type="number" name="count" value="1" min="1" required /></div>
          <div class="row"><label>Date</label><input type="date" name="date" /></div>
          <div class="row"><label>Message</label><input type="text" name="message" placeholder="Main label message" /></div>
          <div class="row"><label>Border Message</label><input type="text" name="border_message" placeholder="Top/Bottom border text" /></div>
          <div class="row"><label>Side Border</label><input type="text" name="side_border" placeholder="Left/Right border text" /></div>
          <div class="row"><label>Image Path</label><input type="text" name="image" placeholder="/path/to/image.png" /></div>
          <div class="row"><label><input type="checkbox" name="list" /> Force printer selection menu</label></div>
          <div class="row"><label><input type="checkbox" name="show_date" /> Show date on label</label></div>
          <div class="row"><label><input type="checkbox" name="preview_only" /> Preview only (no print)</label></div>
          <button type="submit" id="submitBtn">Submit</button>
        </form>
        <div id="status" class="status"></div>
        <h2>Result</h2>
        <pre id="result"></pre>
        <script>
        const form = document.getElementById('labelForm');
        const submitBtn = document.getElementById('submitBtn');
        const statusEl = document.getElementById('status');
        form.addEventListener('submit', async (e) => {
          e.preventDefault();
          const data = new FormData(form);
          const payload = {
            list: data.get('list') === 'on',
            count: data.get('count') ? Number(data.get('count')) : undefined,
            date: data.get('date') || undefined,
            message: data.get('message') || undefined,
            border_message: data.get('border_message') || undefined,
            side_border: data.get('side_border') || undefined,
            image: data.get('image') || undefined,
            show_date: data.get('show_date') === 'on',
            preview_only: data.get('preview_only') === 'on',
          };
          statusEl.textContent = '';
          statusEl.className = 'status';
          submitBtn.disabled = true;
          submitBtn.textContent = 'Submitting...';
          const res = await fetch('/app/pi-label/print', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          let body;
          try { body = await res.json(); } catch (_) { body = await res.text(); }
          document.getElementById('result').textContent = typeof body === 'string' ? body : JSON.stringify(body, null, 2);
          statusEl.textContent = res.ok ? 'OK: Print command executed' : 'Error: See details below';
          statusEl.className = 'status ' + (res.ok ? 'ok' : 'err');
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit';
        });
        </script>
        """,
        mimetype="text/html",
    )


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


@app.route('/app/pi-label/print', methods=['POST'])
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


if __name__ == "__main__":
    # Simple dev server for local testing
    app.run(host="0.0.0.0", port=5000, debug=False)
