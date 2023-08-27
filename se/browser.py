# Copyright 2022-2023 Laurent Defert
#
#  This file is part of SOSSE.
#
# SOSSE is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SOSSE is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with SOSSE.
# If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import pytz
import shlex
import traceback
from datetime import datetime
from time import sleep
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.conf import settings
from PIL import Image
import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from urllib3.exceptions import HTTPError

from .url import absolutize_url, sanitize_url, url_remove_fragment, url_remove_query_string
from .utils import human_filesize

crawl_logger = logging.getLogger('crawler')


def dict_merge(a, b):
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            dict_merge(a[key], b[key])
        else:
            a[key] = b[key]
    return a


class AuthElemFailed(Exception):
    def __init__(self, page, *args, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)


class SkipIndexing(Exception):
    pass


class PageTooBig(SkipIndexing):
    def __init__(self, size, conf_size):
        size = human_filesize(size)
        conf_size = human_filesize(conf_size * 1024)
        super().__init__(f'Document size is too big ({size} > {conf_size}). You can increase the `max_file_size` and `max_html_asset_size` option in the configuration to index this file.')


class TooManyRedirects(SkipIndexing):
    def __init__(self):
        super().__init__(f'Max redirects ({settings.SOSSE_MAX_REDIRECTS}) reached. You can increase the `max_redirects` option in the configuration file in case it\'s needed.')


class Page:
    def __init__(self, url, content, browser, mimetype=None, headers=None, status_code=None):
        assert isinstance(content, bytes)
        self.url = sanitize_url(url)
        self.content = content
        self.redirect_count = 0
        self.title = None
        self.soup = None
        self.browser = browser
        self.mimetype = mimetype
        self.headers = headers or {}
        self.status_code = status_code

    def get_soup(self):
        if self.soup:
            return self.soup
        try:
            content = self.content.decode('utf-8')
        except UnicodeDecodeError:
            return None

        self.soup = BeautifulSoup(content, 'html5lib')

        # Remove <template> tags as BS extract its text
        for elem in self.soup.find_all('template'):
            elem.extract()
        return self.soup

    def get_links(self, keep_params):
        for a in self.get_soup().find_all('a'):
            if a.get('href'):
                url = absolutize_url(self.url, a.get('href').strip())
                if not keep_params:
                    url = url_remove_query_string(url)
                url = url_remove_fragment(url)
                yield url

    def update_soup(self, soup):
        self.soup = soup

    def dump_html(self):
        return self.get_soup().encode()

    def base_url(self):
        soup = self.get_soup()

        base_url = self.url
        if soup.head.base and soup.head.base.get('href'):
            base_url = absolutize_url(self.url, soup.head.base.get('href'))
            base_url = url_remove_fragment(base_url)
        return base_url


class Browser:
    inited = False

    @classmethod
    def init(cls):
        if cls.inited:
            return
        crawl_logger.debug('Browser init')
        RequestBrowser.init()
        SeleniumBrowser.init()
        cls.inited = True

    @classmethod
    def destroy(cls):
        if not cls.inited:
            return
        crawl_logger.debug('Browser destroy')
        RequestBrowser.destroy()
        SeleniumBrowser.destroy()
        cls.inited = False


class RequestBrowser(Browser):
    @classmethod
    def init(cls):
        pass

    @classmethod
    def destroy(cls):
        pass

    @classmethod
    def _page_from_request(cls, r):
        content = r._content
        mimetype = r.headers.get('content-type') or 'application/octet-stream'
        if ';' in mimetype:
            mimetype, _ = mimetype.split(';', 1)

        page = Page(r.url, content, cls, mimetype, r.headers, r.status_code)
        soup = page.get_soup()
        if soup:
            page.title = soup.title and soup.title.string
        return page

    @classmethod
    def _set_cookies(cls, url, cookies):
        from .models import Cookie
        _cookies = []

        for cookie in cookies:
            expires = cookie.expires
            if expires:
                expires = datetime.fromtimestamp(expires, pytz.utc)

            c = {
                'domain': cookie.get_nonstandard_attr('Domain'),
                'name': cookie.name,
                'value': cookie.value,
                'path': cookie.path,
                'expires': expires,
                'secure': cookie.secure,
                'same_site': cookie.get_nonstandard_attr('SameSite'),
                'http_only': cookie.has_nonstandard_attr('HttpOnly')
            }
            _cookies.append(c)

        Cookie.set(url, _cookies)

    @classmethod
    def _get_cookies(cls, url):
        from .models import Cookie
        jar = requests.cookies.RequestsCookieJar()

        for c in Cookie.get_from_url(url):
            expires = None
            if c.expires:
                expires = int(c.expires.strftime('%s'))

            rest = {'SameSite': c.same_site}
            if c.http_only:
                rest['HttpOnly'] = c.http_only,
            jar.set(c.name, c.value, path=c.path, domain=c.domain, expires=expires, secure=c.secure, rest=rest)
        crawl_logger.debug('loading cookies for %s: %s', url, jar)
        return jar

    @classmethod
    def _requests_params(cls):
        params = {
            'stream': True,
            'allow_redirects': False,
            'headers': {
                'User-Agent': settings.SOSSE_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
        }

        if settings.SOSSE_PROXY:
            params['proxies'] = {
                'http': settings.SOSSE_PROXY,
                'https': settings.SOSSE_PROXY
            }
        if settings.SOSSE_REQUESTS_TIMEOUT:
            params['timeout'] = settings.SOSSE_REQUESTS_TIMEOUT
        return params

    @classmethod
    def _requests_query(cls, method, url, max_file_size, **kwargs):
        jar = cls._get_cookies(url)
        crawl_logger.debug('from the jar: %s', jar)
        s = requests.Session()
        s.cookies = jar

        func = getattr(s, method)
        kwargs = dict_merge(cls._requests_params(), kwargs)
        r = func(url, **kwargs)
        cls._set_cookies(url, s.cookies)

        content_length = int(r.headers.get('content-length', 0))
        if content_length / 1024 > max_file_size:
            r.close()
            raise PageTooBig(content_length, max_file_size)

        content = b''
        for chunk in r.iter_content(chunk_size=1024):
            content += chunk
            if len(content) / 1024 >= max_file_size:
                break
        r.close()

        if len(content) / 1024 > max_file_size:
            raise PageTooBig(len(content), max_file_size)

        r._content = content
        crawl_logger.debug('after request jar: %s', s.cookies)
        return r

    @classmethod
    def get(cls, url, check_status=False, max_file_size=settings.SOSSE_MAX_FILE_SIZE, **kwargs):
        Browser.init()
        REDIRECT_CODE = (301, 302, 307, 308)
        page = None
        redirect_count = 0

        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            r = cls._requests_query('get', url, max_file_size, **kwargs)

            if check_status:
                r.raise_for_status()

            if r.status_code in REDIRECT_CODE:
                crawl_logger.debug('%s: redirected' % url)
                redirect_count += 1
                dest = r.headers.get('location')
                url = absolutize_url(url, dest)
                url = url_remove_fragment(url)
                crawl_logger.debug('got redirected to %s' % url)
                if not url:
                    raise Exception('Got a %s code without a location header' % r.status_code)

                continue

            page = cls._page_from_request(r)

            # Check for an HTML / meta redirect
            soup = page.get_soup()
            if soup:
                for meta in page.get_soup().find_all('meta'):
                    if meta.get('http-equiv', '').lower() == 'refresh' and meta.get('content', ''):
                        # handle redirect
                        dest = meta.get('content')

                        if ';' in dest:
                            dest = dest.split(';', 1)[1]

                        if dest.startswith('url='):
                            dest = dest[4:]

                        url = absolutize_url(url, dest)
                        url = url_remove_fragment(url)
                        redirect_count += 1
                        crawl_logger.debug('%s: html redirected' % url)
                        continue
            break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        page.redirect_count = redirect_count
        return page

    @classmethod
    def try_auth(cls, page, url, crawl_policy):
        Browser.init()

        parsed = page.get_soup()
        form = parsed.select(crawl_policy.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(page, 'Could not find element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise AuthElemFailed(page, 'Found multiple element with CSS selector: %s' % crawl_policy.auth_form_selector)

        form = form[0]
        payload = {}
        for elem in form.find_all('input'):
            if elem.get('name'):
                payload[elem.get('name')] = elem.get('value')

        for f in crawl_policy.authfield_set.values('key', 'value'):
            payload[f['key']] = f['value']

        post_url = form.get('action')
        if post_url:
            post_url = absolutize_url(page.url, post_url)
            post_url = url_remove_fragment(post_url)
        else:
            post_url = page.url

        crawl_logger.debug('authenticating to %s with %s', post_url, payload)
        r = cls._requests_query('post', post_url, settings.SOSSE_MAX_FILE_SIZE, data=payload)
        if r.status_code != 302:
            crawl_logger.debug('no redirect after auth')
            return cls._page_from_request(r)

        location = r.headers.get('location')
        if not location:
            raise Exception('No location in the redirection')

        location = absolutize_url(r.url, location)
        location = url_remove_fragment(location)
        crawl_logger.debug('got redirected to %s after authentication' % location)
        return cls.get(location)


def retry(f):
    def _retry(*args, **kwargs):
        count = 0
        while count <= settings.SOSSE_BROWSER_CRASH_RETRY:
            try:
                r = f(*args, **kwargs)
                crawl_logger.debug('%s succeeded' % f)
                return r
            except (WebDriverException, HTTPError):
                exc = traceback.format_exc()
                crawl_logger.error('%s failed' % f)
                crawl_logger.error('Selenium returned an exception:\n%s' % exc)

                cls = args[0]
                cls.destroy()
                sleep(settings.SOSSE_BROWSER_CRASH_SLEEP)
                cls.init()

                if count == settings.SOSSE_BROWSER_CRASH_RETRY:
                    raise
                count += 1
                crawl_logger.error('Retrying (%i / %i)' % (count, settings.SOSSE_BROWSER_CRASH_RETRY))
    return _retry


class SeleniumBrowser(Browser):
    driver = None
    cookie_loaded = []
    COOKIE_LOADED_SIZE = 1024
    first_init = True

    @classmethod
    def init(cls):
        # force the cwd in case it's not called from the worker
        if not os.getcwd().startswith(settings.SOSSE_TMP_DL_DIR + '/'):
            os.chdir(settings.SOSSE_TMP_DL_DIR + '/0')

        options = Options()
        options.binary_location = "/usr/bin/chromium"

        opts = shlex.split(settings.SOSSE_BROWSER_OPTIONS)

        if settings.SOSSE_PROXY:
            opts.append('--proxy-server=%s' % settings.SOSSE_PROXY.rstrip('/'))
        opts.append('--user-agent=%s' % settings.SOSSE_USER_AGENT)
        opts.append('--start-maximized')
        opts.append('--start-fullscreen')
        opts.append('--window-size=%s,%s' % cls.screen_size())

        for opt in opts:
            if cls.first_init:
                crawl_logger.info('Passing option %s', opt)
            options.add_argument(opt)

        cls.first_init = False
        cls.driver = webdriver.Chrome(options=options)
        cls.driver.delete_all_cookies()

    @classmethod
    def destroy(cls):
        if cls.driver:
            # Ignore errors in case the browser crashed
            try:
                cls.driver.close()
            except:  # noqa
                pass

            try:
                cls.driver.quit()
            except:  # noqa
                pass

    @classmethod
    def _current_url(cls):
        if cls.driver.current_url.startswith('data:'):
            return ''
        return sanitize_url(cls.driver.current_url)

    @classmethod
    def _wait_for_ready(cls, url):
        redirect_count = 0
        while redirect_count <= settings.SOSSE_MAX_REDIRECTS:
            # Wait for page being ready
            retry = settings.SOSSE_JS_STABLE_RETRY
            while retry > 0 and cls.driver.current_url == url:
                retry -= 1
                if cls.driver.execute_script('return document.readyState;') == 'complete':
                    break

            if cls.driver.current_url != url:
                redirect_count += 1
                url = cls.driver.current_url
                continue
            else:
                break

            # Wait for page content to be stable
            retry = settings.SOSSE_JS_STABLE_RETRY
            previous_content = None
            content = None

            while retry > 0 and cls.driver.current_url == url:
                retry -= 1
                content = cls.driver.page_source

                if content == previous_content:
                    break
                previous_content = content
                sleep(settings.SOSSE_JS_STABLE_TIME)

            if cls.driver.current_url != url:
                redirect_count += 1
                url = cls.driver.current_url
                continue
            else:
                break

        if redirect_count > settings.SOSSE_MAX_REDIRECTS:
            raise TooManyRedirects()

        return redirect_count

    @classmethod
    def remove_nav_elements(cls):
        cls.driver.execute_script('''
        const tags = ['nav', 'header', 'footer'];
        tags.map((tag) => {
            const elems = document.getElementsByTagName(tag);
            for (no = 0; no < elems.length; no++) {
                elems[no].remove();
            }
        });
        ''')

    @classmethod
    def _get_page(cls, url):
        from .models import CrawlPolicy
        redirect_count = cls._wait_for_ready(url)

        current_url = cls._current_url()
        crawl_policy = CrawlPolicy.get_from_url(current_url)
        if crawl_policy and crawl_policy.script:
            cls.driver.execute_script(crawl_policy.script)
            cls._wait_for_ready(url)

        if crawl_policy and crawl_policy.remove_nav_elements == CrawlPolicy.REMOVE_NAV_YES:
            cls.remove_nav_elements()

        content = cls.driver.page_source.encode('utf-8')
        page = Page(current_url,
                    content,
                    cls)
        page.title = cls.driver.title
        page.redirect_count = redirect_count
        return page

    @classmethod
    def _save_cookies(cls, url):
        from .models import Cookie
        _cookies = []
        crawl_logger.debug('got cookies %s' % cls.driver.get_cookies())
        for cookie in cls.driver.get_cookies():
            c = {
                'name': cookie['name'],
                'value': cookie['value'],
                'path': cookie['path'],
                'secure': cookie['secure'],
            }

            expires = cookie.get('expiry')
            if expires:
                c['expires'] = datetime.fromtimestamp(expires, pytz.utc)

            if cookie.get('sameSite'):
                c['same_site'] = cookie['sameSite']

            if cookie.get('httpOnly'):
                c['http_only'] = cookie['httpOnly']

            if cookie.get('domain'):
                c['domain'] = cookie['domain']

            _cookies.append(c)

        Cookie.set(url, _cookies)

    @classmethod
    def _load_cookies(cls, url):
        from .models import Cookie

        if url.startswith('data:'):
            return

        # Cookies can only be set to the same domain,
        # so first we navigate to the correct location
        current_url = urlparse(cls._current_url())
        dest = sanitize_url(url)
        target_url = urlparse(dest)
        cookies = Cookie.get_from_url(dest)
        if len(cookies) == 0:
            crawl_logger.debug('no cookie to load for %s' % dest)
            return

        if current_url.netloc != target_url.netloc:
            crawl_logger.debug('navigate for cookie to %s' % dest)
            cls.driver.get(dest)

        crawl_logger.debug('clearing cookies')
        cls.driver.delete_all_cookies()
        for c in cookies:
            cookie = {
                'name': c.name,
                'value': c.value,
                'path': c.path,
                'secure': c.secure,
                'sameSite': c.same_site.title(),
            }
            if c.domain_cc:
                cookie['domain'] = c.domain_cc
            if c.expires:
                cookie['expiry'] = int(c.expires.strftime('%s'))
            if c.http_only:
                cookie['httpOnly'] = c.http_only
            try:
                cls.driver.add_cookie(cookie)
                crawl_logger.debug('loaded cookie %s' % cookie)
            except:  # noqa
                raise Exception('%s\n%s' % (cookie, cls.driver.current_url))

    @classmethod
    @retry
    def get(cls, url):
        Browser.init()

        current_url = cls.driver.current_url

        # Clear the download dir
        for f in os.listdir('.'):
            if os.path.isfile(f):
                crawl_logger.warning('Deleting stale download file %s (you may fix the issue by adjusting "dl_check_*" variables in the conf)' % f)
                os.unlink(f)

        crawl_logger.debug('loading cookies')
        cls._load_cookies(url)
        crawl_logger.debug('driver get')
        cls.driver.get(url)

        if ((current_url != url and cls.driver.current_url == current_url)  # If we got redirected to the url that was previously set in the browser
                or cls.driver.current_url == 'data:,'):  # The url can be "data:," during a few milliseconds when the download starts
            crawl_logger.debug('download starting')
            page = cls._handle_download(url)
            if page:
                return page

        crawl_logger.debug('page get')
        page = cls._get_page(url)
        crawl_logger.debug('save cookies')
        cls._save_cookies(url)
        return page

    @classmethod
    def _handle_download(cls, url):
        retry = settings.SOSSE_DL_CHECK_RETRY
        while retry:
            if len(os.listdir('.')) != 0:
                break
            crawl_logger.debug('no download in progress')
            sleep(settings.SOSSE_DL_CHECK_TIME)
            retry -= 1
        else:
            if len(os.listdir('.')) == 0:  # redo the check in case SOSSE_DL_CHECK_RETRY == 0
                crawl_logger.debug('no download has started')
                return

        crawl_logger.debug('Download in progress: %s' % os.listdir('.'))
        filename = os.listdir('.')[0]
        size = os.stat(filename).st_size
        while True:
            sleep(settings.SOSSE_DL_CHECK_TIME)
            try:
                _size = os.stat(filename).st_size
            except FileNotFoundError:
                # when the download is finished the file is renamed
                break
            if size == _size:
                break
            size = _size

            if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
                SeleniumBrowser.destroy()  # cancel the download
                raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)

        crawl_logger.debug('Download done: %s' % os.listdir('.'))

        filename = os.listdir('.')[0]
        size = os.stat(filename).st_size
        if size / 1024 > settings.SOSSE_MAX_FILE_SIZE:
            raise PageTooBig(size, settings.SOSSE_MAX_FILE_SIZE)
        with open(filename, 'rb') as f:
            content = f.read()

        page = Page(url, content, cls)

        # Remove all files in case multiple were downloaded
        for f in os.listdir('.'):
            if os.path.isfile(f):
                os.unlink(f)
        return page

    @classmethod
    def screen_size(cls):
        w, h = settings.SOSSE_SCREENSHOTS_SIZE.split('x')
        return int(w), int(h)

    @classmethod
    @retry
    def create_thumbnail(cls, url, image_name):
        width, height = cls.screen_size()
        cls.driver.set_window_rect(0, 0, *cls.screen_size())
        cls.driver.execute_script('document.body.style.overflow = "hidden"')

        base_name = os.path.join(settings.SOSSE_THUMBNAILS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)
        thumb_png = base_name + '.png'
        thumb_jpg = base_name + '.jpg'

        try:
            cls.driver.get_screenshot_as_file(thumb_png)
            with Image.open(thumb_png) as img:
                img = img.convert('RGB')  # Remove alpha channel from the png
                img.thumbnail((160, 100))
                img.save(thumb_jpg, 'jpeg')
        finally:
            if os.path.exists(thumb_png):
                os.unlink(thumb_png)

    @classmethod
    @retry
    def take_screenshots(cls, url, image_name):
        base_name = os.path.join(settings.SOSSE_SCREENSHOTS_DIR, image_name)
        dir_name = os.path.dirname(base_name)
        os.makedirs(dir_name, exist_ok=True)

        width, height = cls.screen_size()
        cls.driver.set_window_rect(0, 0, *cls.screen_size())
        cls.driver.execute_script('document.body.style.overflow = "hidden"')
        doc_height = cls.driver.execute_script('''
            const body = document.body;
            const html = document.documentElement;
            return height = Math.max(body.scrollHeight, body.offsetHeight,
                                   html.clientHeight, html.scrollHeight, html.offsetHeight);
        ''')

        img_no = 0
        while (img_no + 1) * height < doc_height:
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (base_name, img_no))
            img_no += 1

        remaining = doc_height - (img_no * height)
        if remaining > 0:
            cls.driver.set_window_rect(0, 0, width, remaining)
            cls.scroll_to_page(img_no)
            cls.driver.get_screenshot_as_file('%s_%s.png' % (base_name, img_no))
            img_no += 1

        return img_no

    @classmethod
    def scroll_to_page(cls, page_no):
        _, height = cls.screen_size()
        height *= page_no
        cls.driver.execute_script('''
            window.scroll(0, %s);
            [...document.querySelectorAll('*')].filter(x => x.clientHeight < x.scrollHeight).forEach(e => {
                e.scroll({left: 0, top: %s, behavior: 'instant'});
            });
        ''' % (height, height))

    @classmethod
    def get_link_pos_abs(cls, selector):
        return cls.driver.execute_script('''
            const e = document.evaluate('%s', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);

            if (e === null) {
                return {}
            };
            let el = e.singleNodeValue;
            if (el === null) {
                return {}
            };
            if (el.children.length === 1 && el.children[0].tagName === 'IMG') {
                el = el.children[0];
            }
            const bodyRect = document.body.getBoundingClientRect();
            const elemRect = el.getBoundingClientRect();
            const pageWidth = %s;
            if (elemRect.left >= pageWidth) {
                return {};
            }
            return {
                elemLeft: elemRect.left,
                elemTop: elemRect.top,
                elemRight: Math.min(pageWidth, elemRect.right),
                elemBottom: elemRect.bottom,
            }
        ''' % (selector, cls.screen_size()[0]))

    @classmethod
    def _find_elements_by_selector(cls, obj, selector):
        if hasattr(obj, 'find_elements_by_css_selector'):
            return obj.find_elements_by_css_selector(selector)

        # Selenium 4
        from selenium.webdriver.common.by import By
        return obj.find_elements(By.CSS_SELECTOR, selector)

    @classmethod
    @retry
    def try_auth(cls, page, url, crawl_policy):
        Browser.init()

        form = cls._find_elements_by_selector(cls.driver, crawl_policy.auth_form_selector)

        if len(form) == 0:
            raise AuthElemFailed(page, 'Could not find auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        if len(form) > 1:
            raise AuthElemFailed(page, 'Found multiple auth element with CSS selector: %s' % crawl_policy.auth_form_selector)

        crawl_logger.debug('form found')
        form = form[0]
        for f in crawl_policy.authfield_set.values('key', 'value'):
            elem = cls._find_elements_by_selector(form, 'input[name="%s"]' % f['key'])
            if len(elem) != 1:
                raise Exception('Found %s input element when trying to set auth field %s' % (len(elem), f['key']))
            elem[0].send_keys(f['value'])
            crawl_logger.debug('settings %s = %s on %s' % (f['key'], f['value'], elem[0]))

        form.submit()
        crawl_logger.debug('submitting')
        current_url = cls._current_url()
        cls._save_cookies(current_url)

        if current_url != url:
            return cls.get(url)

        return cls._get_page(url)
