import asyncio
import multiprocessing
import pickle
import cv2
import base64
import threading

from template import HTML5Template
from time import sleep
from multiprocessing import Event, JoinableQueue

from sanic import Sanic
from sanic import response
from sanic.response import json, stream

from realsense import Realsense, REALSENSE_STREAM_WINDOW

app = Sanic(__name__)
app.static('/static', './static')

NUMBER_OF_CORES = multiprocessing.cpu_count()
DEBUG = True
PORT = 5901
HOST = '127.0.0.1'

class Hephaestus():
    def __init__(self, host=HOST, port=PORT, workers=NUMBER_OF_CORES, debug=DEBUG):
        self._host = host
        self._port = port
        self._workers = workers
        self._debug = debug
        self._img_queue = JoinableQueue()
        self._template = HTML5Template()

    def run(self):
        stop = Event()

        @app.route('/')
        async def index(request):
            return response.html(self._template.index)

        async def realsense_stream(response):
            while not stop.is_set():
                img = self._img_queue.get()
                self._img_queue.task_done()
                frame = cv2.imencode('.jpg', img)[1].tobytes()
                response.write(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        @app.route('/camera-stream/')
        async def camera_stream(request):
            return stream(realsense_stream, content_type='multipart/x-mixed-replace; boundary=frame')

        @app.listener('before_server_stop')
        async def notify_server_stopping(app, loop):
            if not stop.is_set():
                stop.set()

        app.run(host=self._host, port=self._port, workers=self._workers, debug=self._debug) 

    def __enter__(self):
        self._realsense = Realsense((640, 480))
        self._realsense.__enter__()

        def realsense_stream():
            while True:
                status, color, depth = self._realsense.next()

                if status:
                    self._img_queue.put(color)
                    self._img_queue.join()

        self._realsense_stream_thread = threading.Thread(target=realsense_stream)
        self._realsense_stream_thread.daemon = True
        self._realsense_stream_thread.start()
        return self

    def __exit__(self, *args):
        if self._realsense:
            self._realsense.__exit__()
        
if __name__ == '__main__':
    with Hephaestus() as hephaestus:
        hephaestus.run()
