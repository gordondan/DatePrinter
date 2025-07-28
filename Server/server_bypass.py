#!/usr/bin/env python
"""
Server that completely bypasses RFC1918 checking by using tornado
"""
import tornado.ioloop
import tornado.web
import subprocess
import html

class DatePrinterHandler(tornado.web.RequestHandler):
    def get(self):
        script_path = 'date-printer.py'
        count_str = self.get_argument('count', '1')
        
        try:
            count_val = int(count_str)
            if count_val <= 0:
                raise ValueError("Count must be positive.")
        except ValueError:
            self.set_status(400)
            self.write("Error: Invalid 'count' parameter.")
            return
        
        try:
            command = ['python', script_path, '-c', str(count_val)]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            output_html = f"""
                <h1>Script Execution Successful</h1>
                <h2>Output from {script_path} (ran {count_val} time(s)):</h2>
                <pre>{html.escape(result.stdout)}</pre>
            """
            self.write(output_html)
        except Exception as e:
            self.set_status(500)
            self.write(f"Error: {str(e)}")

def make_app():
    return tornado.web.Application([
        (r"/app/date-printer", DatePrinterHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(5000, address='0.0.0.0')
    print("\nTornado server running on:")
    print("  Local: http://127.0.0.1:5000/app/date-printer")
    print("  Public: http://thunderbelly.duckdns.org/app/date-printer\n")
    print("Press Ctrl+C to stop")
    
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        tornado.ioloop.IOLoop.current().stop()