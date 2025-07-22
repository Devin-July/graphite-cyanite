from unittest.mock import patch
from unittest import TestCase
import requests

from cyanite import CyaniteFinder, chunk, URLs, CyaniteReader, CyaniteLeafNode
from graphite_api.storage import FindQuery
from graphite_api.intervals import IntervalSet


class CyaniteTests(TestCase):
    def test_conf(self):
        config = {'cyanite': {'urls': ['https://host1:8080',
                                       'https://host2:9090']}}
        CyaniteFinder(config)
        from cyanite import urls
        self.assertEqual(urls.host, 'https://host1:8080')
        self.assertEqual(urls.host, 'https://host2:9090')
        self.assertEqual(urls.host, 'https://host1:8080')

    @patch('requests.get')
    def test_metrics(self, get):
        get.return_value.json.return_value = [
            {'path': 'foo.',
             'leaf': 0},
            {'path': 'foo.bar',
             'leaf': 1},
        ]
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('foo.*', 50, 100)
        branch, leaf = list(finder.find_nodes(query))
        self.assertEqual(leaf.path, 'foo.bar')
        self.assertEqual(branch.path, 'foo.')
        get.assert_called_once_with('https://host:8080/paths',
                                    params={'query': 'foo.*', 'from': 50, 'to': 100}, timeout=3)

        get.reset_mock()
        get.return_value.json.return_value = {
            'from': 50,
            'to': 100,
            'step': 1,
            'series': {'foo.bar': list(range(50))},
        }

        time_info, data = leaf.reader.fetch(50, 100)
        self.assertEqual(time_info, (50, 100, 1))
        self.assertEqual(data, list(range(50)))

        get.assert_called_once_with('https://host:8080/metrics',
                                    params={'to': 100,
                                            'path': 'foo.bar',
                                            'from': 50})

    @patch('requests.post')
    @patch('requests.get')
    def test_fetch_multi(self, get, post):
        get.return_value.json.return_value = [
            {'path': 'foo.baz',
             'leaf': 1},
            {'path': 'foo.bar',
             'leaf': 1},
        ]

        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('foo.*', 50, 100)
        nodes = list(finder.find_nodes(query))

        get.reset_mock()
        post.return_value.json.return_value = {
            'from': 50,
            'to': 100,
            'step': 1,
            'series': {'foo.bar': list(range(50)),
                       'foo.baz': list(range(50))},
        }

        time_info, series = finder.fetch_multi(nodes, 50, 100)
        self.assertEqual(set(series.keys()), set(['foo.bar', 'foo.baz']))

    def test_chunk(self):
        mylist = range(1000, 9999)
        self.assertEqual(len(list(chunk(mylist, 4))), 9000)

    def test_django_configuration_requires_django(self):
        with self.assertRaises((ImportError, ModuleNotFoundError)):
            CyaniteFinder(config=None)

    def test_single_url_config(self):
        config = {'cyanite': {'url': 'https://single:8080/'}}
        CyaniteFinder(config)
        from cyanite import urls
        self.assertEqual(urls.host, 'https://single:8080')

    def test_optional_config_parameters(self):
        config = {'cyanite': {
            'url': 'https://host:8080',
            'urllength': 5000,
            'find_timeout': 5,
            'fetch_timeout': 15
        }}
        CyaniteFinder(config)
        from cyanite import urllength, find_timeout, fetch_timeout
        self.assertEqual(urllength, 5000)
        self.assertEqual(find_timeout, 5)
        self.assertEqual(fetch_timeout, 15)

    def test_urls_round_robin(self):
        urls = URLs(['https://host1:8080', 'https://host2:9090', 'https://host3:7070'])
        self.assertEqual(urls.host, 'https://host1:8080')
        self.assertEqual(urls.host, 'https://host2:9090')
        self.assertEqual(urls.host, 'https://host3:7070')
        self.assertEqual(urls.host, 'https://host1:8080')

    def test_urls_properties(self):
        urls = URLs(['https://test:8080'])
        self.assertEqual(urls.paths, 'https://test:8080/paths')
        self.assertEqual(urls.metrics, 'https://test:8080/metrics')

    def test_urls_single_host(self):
        urls = URLs(['https://single:8080'])
        self.assertEqual(urls.host, 'https://single:8080')
        self.assertEqual(urls.host, 'https://single:8080')

    @patch('requests.get')
    def test_cyanite_reader_error_response(self, mock_get):
        import cyanite
        cyanite.urls = URLs(['https://test:8080'])
        
        mock_get.return_value.json.return_value = {'error': 'Something went wrong'}
        reader = CyaniteReader('test.path')
        result = reader.fetch(100, 200)
        self.assertEqual(result, ((100, 200, 100), []))

    @patch('requests.get')
    def test_cyanite_reader_empty_series(self, mock_get):
        import cyanite
        cyanite.urls = URLs(['https://test:8080'])
        
        mock_get.return_value.json.return_value = {'series': {}}
        reader = CyaniteReader('test.path')
        result = reader.fetch(100, 200)
        self.assertIsNone(result)

    @patch('requests.get')
    def test_cyanite_reader_missing_path(self, mock_get):
        import cyanite
        cyanite.urls = URLs(['https://test:8080'])
        
        mock_get.return_value.json.return_value = {
            'from': 100, 'to': 200, 'step': 1,
            'series': {'other.path': [1, 2, 3]}
        }
        reader = CyaniteReader('test.path')
        time_info, data = reader.fetch(100, 200)
        self.assertEqual(time_info, (100, 200, 1))
        self.assertEqual(data, [])

    @patch('requests.get')
    def test_cyanite_reader_successful_fetch(self, mock_get):
        import cyanite
        cyanite.urls = URLs(['https://test:8080'])
        
        mock_get.return_value.json.return_value = {
            'from': 100, 'to': 200, 'step': 1,
            'series': {'test.path': [1, 2, 3, 4, 5]}
        }
        reader = CyaniteReader('test.path')
        time_info, data = reader.fetch(100, 200)
        self.assertEqual(time_info, (100, 200, 1))
        self.assertEqual(data, [1, 2, 3, 4, 5])

    def test_cyanite_reader_get_intervals(self):
        reader = CyaniteReader('test.path')
        intervals = reader.get_intervals()
        self.assertIsInstance(intervals, IntervalSet)

    @patch('requests.get')
    def test_find_nodes_http_error(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection failed")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('foo.*', 50, 100)
        
        with self.assertRaises(ConnectionError):
            list(finder.find_nodes(query))

    @patch('requests.get')
    def test_find_nodes_timeout(self, mock_get):
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Request timed out")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('foo.*', 50, 100)
        
        with self.assertRaises(Timeout):
            list(finder.find_nodes(query))

    @patch('requests.get')
    def test_find_nodes_invalid_json(self, mock_get):
        mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('foo.*', 50, 100)
        
        with self.assertRaises(ValueError):
            list(finder.find_nodes(query))

    @patch('requests.post')
    def test_fetch_multi_error_response(self, mock_post):
        mock_post.return_value.json.return_value = {'error': 'Server error'}
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        nodes = [CyaniteLeafNode('test.path', CyaniteReader('test.path'))]
        
        time_info, series = finder.fetch_multi(nodes, 100, 200)
        self.assertEqual(time_info, (100, 200, 100))
        self.assertEqual(series, {})

    @patch('requests.post')
    def test_fetch_multi_http_error(self, mock_post):
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError("Connection failed")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        nodes = [CyaniteLeafNode('test.path', CyaniteReader('test.path'))]
        
        with self.assertRaises(ConnectionError):
            finder.fetch_multi(nodes, 100, 200)

    @patch('requests.post')
    def test_fetch_multi_timeout(self, mock_post):
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout("Request timed out")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        nodes = [CyaniteLeafNode('test.path', CyaniteReader('test.path'))]
        
        with self.assertRaises(Timeout):
            finder.fetch_multi(nodes, 100, 200)

    @patch('requests.post')
    def test_fetch_multi_invalid_json(self, mock_post):
        mock_post.return_value.json.side_effect = ValueError("Invalid JSON")
        
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        nodes = [CyaniteLeafNode('test.path', CyaniteReader('test.path'))]
        
        with self.assertRaises(ValueError):
            finder.fetch_multi(nodes, 100, 200)

    @patch('requests.get')
    def test_find_nodes_with_cache(self, mock_get):
        import cyanite
        finder = CyaniteFinder({'cyanite': {'url': 'https://host:8080'}})
        query = FindQuery('cached.pattern', 50, 100)
        
        cyanite.leafcache['cached.pattern'] = True
        
        nodes = list(finder.find_nodes(query))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].path, 'cached.pattern')
        mock_get.assert_not_called()

    def test_missing_config_key(self):
        with self.assertRaises(KeyError):
            CyaniteFinder({'other': {'url': 'https://host:8080'}})
