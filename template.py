import os

INDEX_FILE = 'index.html'

class HTML5Template():
    def __init__(self, index_file=INDEX_FILE, dir='.'):
        self._index = None

        if os.path.isfile(index_file):
            with open(index_file, 'rb') as index:
                self._index = index.read().decode('utf-8')
                print(self._index)
        else:
            raise AssertionError('No file named "%s" was found' % (index_file,))

    @property
    def index(self):
        return self._index