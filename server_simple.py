# Simple server without host validation
from flask import Flask, Response, request
import subprocess
import socket
import html

app = Flask(__name__)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        if 's' in locals():
            s.close()
    return ip

@app.route('/app/date-printer', methods=['GET'])
def run_date_printer():
    script_path = 'date-printer.py'
    count_str = request.args.get('count', '1')

    try:
        count_val = int(count_str)
        if count_val <= 0:
            raise ValueError("Count must be positive.")
    except ValueError:
        return Response("Error: Invalid 'count' parameter.", status=400)
    
    try:
        command = ['python', script_path, '-c', str(count_val)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        output_html = f"""
            <h1>Script Execution Successful</h1>
            <h2>Output from {script_path} (ran {count_val} time(s)):</h2>
            <pre>{html.escape(result.stdout)}</pre>
        """
        return Response(output_html, mimetype='text/html')
    except Exception as e:
        return Response(f"Error: {str(e)}", status=500)

if __name__ == '__main__':
    PORT = 5000
    HOST_IP = get_local_ip()
    
    print(f"\nServer running on:")
    print(f"  Local: http://127.0.0.1:{PORT}/app/date-printer")
    print(f"  Network: http://{HOST_IP}:{PORT}/app/date-printer")
    print(f"  Public: http://thunderbelly.duckdns.org/app/date-printer\n")
    
    # Use threaded server without debug mode
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', PORT, app, threaded=True, use_reloader=False, use_debugger=False)