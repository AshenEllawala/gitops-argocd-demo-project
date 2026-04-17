from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
    version = os.environ.get('APP_VERSION', '1.0.0')
    build = os.environ.get('BUILD_NUMBER', 'local')
    return render_template('index.html', version=version, build=build)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)