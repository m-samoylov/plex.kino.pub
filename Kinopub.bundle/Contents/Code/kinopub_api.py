# -*- coding: utf-8 -*-

import urllib2
import urllib
import json
import time

API_URL = "http://api.kino.pub/v1"
OAUTH_API_URL = "http://api.kino.pub/oauth2/device"
CLIENT_ID = "plex"
CLIENT_SECRET = "h2zx6iom02t9cxydcmbo9oi0llld7jsv"

class API(object):
    STATUS_ERROR, STATUS_PENDING, STATUS_SUCCESS, STATUS_EXPIRED = range(4)
    def __init__(self, settings={}, HTTPHandler=None):
        self.settings = settings
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.HTTPHandler = HTTPHandler

    @property
    def access_token(self):
        return self.settings.get('access_token')
    @access_token.setter
    def access_token(self, value):
        self.settings.set('access_token', value)

    @property
    def access_token_expire(self):
        try:
            return int(self.settings.get('access_token_expire'))
        except:
            return 0
    @access_token_expire.setter
    def access_token_expire(self, value):
        self.settings.set('access_token_expire', int(value))

    @property
    def device_code(self):
        return self.settings.get('device_code')
    @device_code.setter
    def device_code(self, value):
        self.settings.set('device_code', value)

    @property
    def device_code_expire(self):
        return int(self.settings.get('device_code_expire'))
    @device_code_expire.setter
    def device_code_expire(self, value):
        try:
            self.settings.set('device_code_expire', int(value))
        except:
            return 0

    @property
    def refresh_token(self):
        return self.settings.get('refresh_token')
    @refresh_token.setter
    def refresh_token(self, value):
        self.settings.set('refresh_token', value)

    @property
    def refresh_token_expire(self):
        return int(self.settings.get('refresh_token_expire'))
    @refresh_token_expire.setter
    def refresh_token_expire(self, value):
        try:
            self.settings.set('refresh_token_expire', int(value))
        except:
            return 0

    @property
    def user_code(self):
        return self.settings.geT('user_code')
    @user_code.setter
    def user_code(self, value):
        self.settings.set('user_code', value)

    @property
    def verification_uri(self):
        return self.settings.get('verification_uri')
    @verification_uri.setter
    def verification_uri(self, value):
        self.settings.set('verification_uri', value)

    def reset_settings(self):
        self.access_token = ''
        self.access_token_expire = int(time.time())
        self.device_code = ''
        self.device_code_expire = int(time.time())
        self.user_code = ''
        self.refresh_token = ''

    def auth_request(self, url, data):
        try:
            udata = urllib.urlencode(data)
            req = urllib2.Request(url)

            resp = urllib2.urlopen(req, udata).read()
            return json.loads(resp)
        except urllib2.URLError, e:
            try:
                if e.code == 400:
                    try:
                        resp = e.read()
                        return json.loads(resp)
                    except:
                        pass
            except:
                pass
            return {'error': 'Service problems'}

    def get_device_code(self, url=OAUTH_API_URL):
        data = {
            'grant_type': 'device_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }
        resp = self.auth_request(url, data)
        error = resp.get('error')
        if error:
            return self.STATUS_ERROR, resp

        self.device_code = resp['code']
        self.user_code = resp['user_code']
        self.verification_uri = resp['verification_uri']
        self.device_code_expire = int(resp.get('expires_in')) + int(time.time())
        return self.STATUS_SUCCESS, resp

    def get_access_token(self, url=OAUTH_API_URL, refresh=False):
        if refresh:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
            }
        else:
            data = {
                'grant_type': 'device_token',
                'code': self.device_code,
            }
        data['client_id'] = self.client_id
        data['client_secret'] = self.client_secret

        resp = self.auth_request(url, data)
        error = resp.get('error')
        if error and error == "authorization_pending":
            return self.STATUS_PENDING, resp
        if error and error in ["invalid_grant", "code_expired", "invalid_client", "invalid_request"]:
            return self.STATUS_EXPIRED, resp

        self.access_token = resp.get('access_token')
        if (self.access_token):
            self.access_token_expire = int(resp.get('expires_in')) + int(time.time())
            self.refresh_token = resp.get('refresh_token')
            # reset device code
            self.device_code = None
            return self.STATUS_SUCCESS, resp

        return self.STATUS_ERROR, resp

    def is_authenticated(self):
        response = self.api_request('types', disableHTTPHandler=True)
        if self.access_token and not self.is_expiring() and response['status'] == 200 and not self.device_code:
            return True

        return False

    def is_expiring(self, token_name="access_token", expire_announce=900):
        try:
            expire = int(self.settings.get(token_name + '_expire'))
        except:
            expire = 0
        if expire - int(time.time()) < expire_announce:
            return True
        return False

    def api_request(self, action, params={}, url=API_URL, timeout=600, disableHTTPHandler=False, cacheTime=3600):
        error_msg = {
            'status': 401,
            'name': 'Unauthorized',
            'message': 'Unauthorized ',
            'code': 0,
        }
        if self.access_token:
            if self.is_expiring():
                if self.refresh_token:
                    status, response = self.get_access_token(refresh=True)
                    if status == self.STATUS_SUCCESS:
                        params['access_token'] = self.access_token
                else:
                    self.reset_settings()
                    error_msg
        elif self.device_code:
            return error_msg
        else:
            self.reset_settings()
            return error_msg

        params['access_token'] = self.access_token
        uparams = urllib.urlencode(params)
        try:
            req_url = "%s/%s?%s" % (url, action, uparams)
            if self.HTTPHandler and not disableHTTPHandler:
                # @TODO: change cache time
                response = str(self.HTTPHandler.Request(req_url, cacheTime=cacheTime)).decode('utf-8')
            else:
                response = urllib2.urlopen(req_url, timeout=timeout).read()
            return json.loads(response)
        except urllib2.HTTPError as e:
            if self.HTTPHandler and not disableHTTPHandler:
                return {
                    'status': 401,
                    'name': 'Unauthorized',
                    'message': 'Unauthorized',
                    'code': 0
                }

            response = e.read()
            return json.loads(response)
        except Exception as e:
            return {
                'status': 105,
                'name': 'Name Not Resolved',
                'message': 'Name not resolved',
                'code': 0
            }
