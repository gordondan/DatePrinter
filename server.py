from flask import Flask, jsonify, request, Response, send_from_directory, send_file
import subprocess
import sys
import os
import html
import re
import time
from pathlib import Path
from datetime import datetime
from urllib.parse import quote, unquote
from PIL import Image

# Try to import BLE printer for direct reprint support
try:
    from rw402b_ble.printer import RW402BPrinter
except Exception:  # noqa: E722
    RW402BPrinter = None


app = Flask(__name__)


@app.route('/', methods=['GET'])
@app.route('/index.html', methods=['GET'])
def root_index():
    """Serve the main UI at the root path for convenience."""
    return send_from_directory(os.path.join(os.path.dirname(__file__), "www"), "index.html")


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


# --- Helpers ---

def _find_latest_preview():
    """Search for the newest label_preview.png under logs/ and project root."""
    base_dir = Path(os.path.dirname(__file__))
    candidates = []
    root_preview = base_dir / "label_preview.png"
    if root_preview.is_file():
        candidates.append(root_preview)

    logs_dir = base_dir / "logs"
    if logs_dir.is_dir():
        try:
            for p in logs_dir.rglob("label_preview.png"):
                if p.is_file():
                    candidates.append(p)
        except Exception:
            pass

    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _find_latest_metrics():
    """If a metrics.json exists next to the latest preview, load and return it."""
    p = _find_latest_preview()
    if not p:
        return None
    metrics_path = p.with_name('metrics.json')
    if metrics_path.is_file():
        try:
            import json
            with open(metrics_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _parse_metrics_from_stdout(stdout: str):
    """Look for a line like 'METRICS: {json}' and parse it."""
    try:
        for line in stdout.splitlines():
            if line.startswith('METRICS:'):
                import json
                payload = line.partition('METRICS:')[2].strip()
                return json.loads(payload)
    except Exception:
        pass
    return None


def _logs_dir() -> Path:
    return Path(os.path.dirname(__file__)) / "logs"


def _list_recent_previews(limit: int = 100):
    base = _logs_dir()
    items = []
    if not base.is_dir():
        return []
    try:
        for p in base.rglob("label_preview.png"):
            try:
                stat = p.stat()
            except Exception:
                continue
            rel = p.relative_to(Path(os.path.dirname(__file__)))
            items.append({
                'path': str(rel).replace('\\', '/'),
                'mtime_ts': int(stat.st_mtime),
                'mtime_iso': datetime.fromtimestamp(stat.st_mtime).isoformat(timespec='seconds'),
                'size': stat.st_size,
            })
        items.sort(key=lambda x: x['mtime_ts'], reverse=True)
        return items[:limit]
    except Exception:
        return []


def _safe_path_from_query(rel_path: str) -> Path | None:
    """Ensure requested path is inside the workspace and under logs/.*"""
    try:
        base = Path(os.path.dirname(__file__))
        target = (base / rel_path).resolve()
        logs = (_logs_dir()).resolve()
        if not str(target).startswith(str(logs)):
            return None
        if not target.is_file():
            return None
        return target
    except Exception:
        return None


def _get_config_file_for_os() -> Path:
    system = sys.platform.lower()
    base = Path(os.path.dirname(__file__))
    if system.startswith('win'):
        return base / 'config' / 'printer-config-windows.json'
    elif system.startswith('linux'):
        return base / 'config' / 'printer-config-linux.json'
    else:
        return base / 'config' / 'printer-config.json'


def _load_printer_config():
    import json as _json
    cfg_path = _get_config_file_for_os()
    if not cfg_path.is_file():
        return None, None
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = _json.load(f)
        printer_name = 'RW402B'
        printers = cfg.get('printers') or {}
        pcfg = printers.get(printer_name) or {
            'label_width_in': 2.25,
            'label_height_in': 1.25,
            'dpi': 203,
            'gap_mm': 3.0,
            'density': 8,
            'speed': 4,
            'direction': 1,
            'invert': True,
            'bluetooth_wait_time': 4.0,
        }
        return cfg, pcfg
    except Exception:
        return None, None


@app.route('/api/recent', methods=['GET'])
def api_recent():
    """Return recent previews with metadata."""
    try:
        limit = int(request.args.get('limit', '100'))
    except Exception:
        limit = 100
    items = _list_recent_previews(limit)
    # attach image URLs
    for it in items:
        q = quote(it['path'])
        it['image_url'] = f"/preview/file?path={q}&ts={it['mtime_ts']}"
    return jsonify({'items': items})


@app.route('/preview/file', methods=['GET'])
def preview_by_path():
    """Serve a specific preview by relative path (under logs directory)."""
    rel = request.args.get('path')
    if not rel:
        return Response('Missing path', mimetype='text/plain'), 400
    rel = unquote(rel)
    p = _safe_path_from_query(rel)
    if not p:
        return Response('Invalid path', mimetype='text/plain'), 400
    resp = send_file(str(p), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@app.route('/api/reprint', methods=['POST'])
def api_reprint():
    """Reprint a saved preview PNG via BLE, best effort."""
    data = request.get_json(silent=True) or {}
    rel = data.get('path')
    if not rel:
        return jsonify({'error': 'Missing path'}), 400
    p = _safe_path_from_query(rel)
    if not p:
        return jsonify({'error': 'Invalid path'}), 400

    if RW402BPrinter is None:
        return jsonify({'error': 'BLE printer module not available on this host'}), 500

    cfg, pcfg = _load_printer_config()
    if pcfg is None:
        return jsonify({'error': 'Printer config not found'}), 500

    try:
        img = Image.open(p)
    except Exception as e:
        return jsonify({'error': f'Failed to open image: {e}'}), 500

    # Pull printer settings
    try:
        dpi = int(pcfg.get('dpi', 203))
        w_in = float(pcfg.get('label_width_in', 2.25))
        h_in = float(pcfg.get('label_height_in', 1.25))
        gap_mm = float(pcfg.get('gap_mm', 3.0))
        density = int(pcfg.get('density', 8))
        speed = int(pcfg.get('speed', 4))
        direction = int(pcfg.get('direction', 1))
        invert = bool(pcfg.get('invert', True))
        ble_mac = pcfg.get('ble_mac') or None
    except Exception as e:
        return jsonify({'error': f'Invalid printer config: {e}'}), 500

    try:
        t0 = time.perf_counter()
        pble = RW402BPrinter(addr=ble_mac, timeout=float(pcfg.get('bluetooth_wait_time', 4.0)),
                              dpi=dpi, invert=invert)
        pble.print_pil_image(
            img,
            label_w_mm=w_in * 25.4,
            label_h_mm=h_in * 25.4,
            gap_mm=gap_mm,
            density=density,
            speed=speed,
            direction=direction,
            x=0, y=0, mode=0
        )
        elapsed_sec = time.perf_counter() - t0
        return jsonify({'ok': True, 'elapsed_sec': round(elapsed_sec, 3)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/preview.png', methods=['GET'])
def latest_preview_png():
    """Serve the most recent label preview PNG."""
    p = _find_latest_preview()
    if not p:
        return Response("Preview not found", mimetype='text/plain'), 404
    # Add a cache-busting header-friendly timestamp
    resp = send_file(str(p), mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


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
        t0 = time.perf_counter()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed_sec = time.perf_counter() - t0

        # Find the latest preview if generated
        preview_path = _find_latest_preview()
        preview_url = None
        if preview_path:
            ts = int(preview_path.stat().st_mtime)
            preview_url = f"/preview.png?ts={ts}"

        metrics = _parse_metrics_from_stdout(result.stdout) or _find_latest_metrics()

        response = {
            'command': cmd,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'elapsed_sec': round(elapsed_sec, 3),
            'preview_url': preview_url,
            'metrics': metrics,
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


@app.route('/recent', methods=['GET'])
def recent_page():
    """Serve the recent labels gallery."""
    return send_from_directory(os.path.join(os.path.dirname(__file__), "www"), "recent.html")


@app.route('/app/date', methods=['GET'])
def app_date_print():
    """Run pi-label-printer.py with default options (today's date) and show result."""
    script_path = os.path.join(os.path.dirname(__file__), 'pi-label-printer.py')
    cmd = [sys.executable or 'python3', script_path, '-o']
    try:
        t0 = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        elapsed_sec = time.perf_counter() - t0
        # Discover preview if available
        preview_path = _find_latest_preview()
        preview_html = ""
        if preview_path:
            ts = int(preview_path.stat().st_mtime)
            preview_html = f"<h2>Preview</h2><img src='/preview.png?ts={ts}' alt='label preview' style='border:1px solid #ddd; max-width:600px;' />"
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
        <div class='status'>{status}: ran pi-label-printer.py (elapsed {elapsed_sec:.3f}s)</div>
        <h2>Command</h2>
        <pre>{html.escape(' '.join(cmd))}</pre>
        <h2>stdout</h2>
        <pre>{html.escape(result.stdout)}</pre>
        <h2>stderr</h2>
        <pre>{html.escape(result.stderr)}</pre>
        {preview_html}
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
