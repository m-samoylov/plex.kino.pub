# -*- coding: utf-8 -*-

import kinopub_api
import kinopub_settings
#import kinopub_http as KHTTP
import urllib2
import urllib
import demjson as json
import time
import sys
sys.setdefaultencoding("utf-8")


ICON                = 'icon-default.png'
ART                 = 'art-default.jpg'
ICON                = 'icon-default.png'
PREFS               = 'icon-prefs.png'
SEARCH              = 'icon-search.png'

PREFIX = '/video/kinopub'

settings = kinopub_settings.Settings(Dict, storage_type="dict")
kpubapi = kinopub_api.API(settings, HTTPHandler=HTTP)
Log("Device ode is : %s " % kpubapi.device_code)
ITEM_URL = kinopub_api.API_URL + '/items'

####################################################################################################
def Start():
    Resource.AddMimeType('image/png','png')
    Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
    Plugin.AddViewGroup('List', viewMode='List', mediaType='items')

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = 'kino.pub'

    DirectoryObject.thumb = R(ICON)
    NextPageObject.thumb = R(ICON)

    PrefsObject.thumb = R(PREFS)
    PrefsObject.art = R(ART)

    InputDirectoryObject.thumb = R(SEARCH)
    InputDirectoryObject.art = R(ART)

    HTTP.CacheTime = CACHE_1HOUR
    #KHTTP.CacheTime = CACHE_1HOUR


# def ValidatePrefs():

def authenticate():
    if kpubapi.is_authenticated():
        return True
    else:
        if settings.get('device_code'):
            # refresh device_code if it expired else device_check code auth
            dev_expire = kpubapi.is_expiring(token_name="device_code", expire_announce=150)
            Log("[authenticate] Devi expire is: %s" % dev_expire)
            if kpubapi.is_expiring(token_name="device_code", expire_announce=150):
                Log("[authenticate] Device code is expired")
                status, response = kpubapi.get_device_code()
                if status == kpubapi.STATUS_SUCCESS:
                    return MessageContainer(settings.get('user_code'), "Посетите %s для активации устройства" % settings.get('verification_uri'))
                return MessageContainer("Ошибка", "Произошла ошибка при обновлении кода устройства, перезапустите плагин.")
            status, response = kpubapi.get_access_token()
            Log("AUTH response status=%s,\n%s" % (status, response))
            if status == kpubapi.STATUS_PENDING:
                return MessageContainer(settings.get('user_code'), "Посетите %s для активации устройства" % settings.get('verification_uri'))
            elif status == kpubapi.STATUS_SUCCESS:
                return True
            return MessageContainer("Ошибка", "Произошла ошибка при авторизации устройства, перезапустите плагин.")
        else:
            status, response = kpubapi.get_device_code()
            if status == kpubapi.STATUS_SUCCESS:
                return MessageContainer(settings.get('user_code'), "Посетите %s для активации устройства" % settings.get('verification_uri'))
            return MessageContainer("Ошибка", "Произошла ошибка при обновлении кода устройства, перезапустите плагин.")

        # try to get API, if 401 error we are not authorized. 
        response = kpubapi.api_request('types', disableHTTPHandler=True)
        if response.get('error') or response.get('status') == 401:
            if int(response.get('status')) == 401:
                kpubapi.reset_settings()
                return MessageContainer("Ошибка", "Устройство не авторизировано. Перезапустите плагин.")
            return MessageContainer("Ошибка", "Не получен ответ от сервера.")

        return True


####################################################################################################
@handler(PREFIX, 'kino.pub', thumb=ICON, art=ART)
def MainMenu():
    result = authenticate()
    if not result == True:
        return result

    oc = ObjectContainer(
        view_group = 'InfoList',
        objects = [
            InputDirectoryObject(
                key     = Callback(Search, item = 'Поиск', title='Поиск'),
                title   = 'Поиск',
                prompt  = 'Поиск'
            ),
        ]
    )

    response = kpubapi.api_request('types')
    Log("MainMenu: response[status] = %s" % response['status'])
    if response['status'] == 200:
        for item in response['items']:
            li = DirectoryObject(
                key = Callback(Items, title=item['title'], qp={'type': item['id']}),
                title = item['title'],
                summary = item['title']
            )
            oc.add(li)
    else:
        return MessageContainer("Ошибка %s" % response['status'], response['message'])
    return oc

@route(PREFIX + '/Items/{type}', qp=dict)
def Items(title, qp=dict):
    response = kpubapi.api_request('items', qp)
    oc = ObjectContainer(title2=title, view_group='InfoList')
    if response['status'] == 200:
        for item in response['items']:
            response2 = kpubapi.api_request('items/%s' % item['id'])
            if response2['status'] == 200:
                videos = response2['item'].get('videos', [])
                Log("LEN OF VID: %s" % len(videos))
                if item['type'] not in ['serial', 'docuserial'] and len(videos) <= 1:
                    # create playable item
                    li = VideoClipObject(
                        url = "%s/%s?access_token=%s#video=1" % (ITEM_URL, item['id'], settings.get('access_token')),
                        title = item['title'],
                        year = int(item['year']),
                        summary = str(item['plot']),
                        genres = [x['title'] for x in item['genres']],
                        directors = item['director'].split(','),
                        countries = [x['title'] for x in item['countries']],
                        content_rating = item['rating'],
                        thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                    )
                    oc.add(li)
                else:
                    # create directory for seasons and multiseries videos
                    li = DirectoryObject(
                        key = Callback(View, title=item['title'], qp={'id': item['id']}),
                        title = item['title'],
                        #summary = unicode(item['plot']),
                        thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                    )
                    oc.add(li)

        # Add "next page" button
        # pagination = response['pagination']
        # if (int(pagination['current'])) + 1 <= int(pagination['total']):
        #     params['page'] = int(pagination['current'])+1
        #     li = NextPageObject(
        #         key = Callback(Items),
        #         title = unicode('Еще...')
        #     )
        #     link = get_internal_link("items", qp)
        #     xbmcplugin.addDirectoryItem(handle, link, li, True)
        # xbmcplugin.endOfDirectory(handle)
    return oc

@route(PREFIX + '/View', qp=dict)
def View(title, qp=dict):
    response = kpubapi.api_request('items/%s' % int(qp['id']))
    oc = ObjectContainer(title2=title, view_group='InfoList')
    if response['status'] == 200:
        item = response['item']
        # prepare serials
        if item['type'] in ['serial', 'docuserial']:
            if 'season' in qp:
                for season in item['seasons']:
                    if int(season['number']) == int(qp['season']):
                        for episode_number, episode in enumerate(season['episodes']):
                            episode_number += 1
                            # create playable item
                            li = VideoClipObject(
                                url = "%s/%s?access_token=%s#season=%s&episode=%s" % (ITEM_URL, item['id'], settings.get('access_token'), season['number'], episode_number),
                                title = episode['title'],
                                year = int(item['year']),
                                summary = str(item['plot']),
                                genres = [x['title'] for x in item['genres']],
                                directors = item['director'].split(','),
                                countries = [x['title'] for x in item['countries']],
                                content_rating = item['rating'],
                                thumb = Resource.ContentsOfURLWithFallback(episode['thumbnail'], fallback=R(ICON))
                            )
                            oc.add(li)
                        break
            else:
                for season in item['seasons']:
                    season_title = season['title'].encode('utf-8') if len(season['title']) > 0 else "Сезон %s" % int(season['number'])
                    li = DirectoryObject(
                        key = Callback(View, title=season_title, qp={'id': item['id'], 'season': season['number']}),
                        title = season_title,
                        summary = season.get('plot', ''),
                        thumb = Resource.ContentsOfURLWithFallback(season['episodes'][0]['thumbnail'], fallback=R(ICON))
                    )
                    oc.add(li)
        #prepare movies, concerts, 3d
        elif 'videos' in item and len(item['videos']) > 1:
            for video_number, video in enumerate(item['videos']):
                video_number += 1
                # create playable item
                li = VideoClipObject(
                    url = "%s/%s?access_token=%s#video=%s" % (ITEM_URL, item['id'], settings.get('access_token'), video_number),
                    title = video['title'],
                    year = int(item['year'],
                    summary = str(item['plot']),
                    genres = [x['title'] for x in item['genres']],
                    directors = item['director'].split(','),
                    countries = [x['title'] for x in item['countries']],
                    content_rating = item['rating'],
                    thumb = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON))
                )
                oc.add(li)
        else:
            video = item['videos'][0]
            video_number = 1
            li = VideoClipObject(
                url = "%s/%s?access_token=%s#video=%s" % (ITEM_URL, item['id'], settings.get('access_token'), video_number),
                title = item['title'],
                year = int(item['year']),
                summary = str(item['plot']),
                genres = [x['title'] for x in item['genres']],
                directors = item['director'].split(','),
                countries = [x['title'] for x in item['countries']],
                content_rating = item['rating'],
                thumb = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON))
            )
            oc.dd(li)
    return oc

@route(PREFIX + '/Search')
def Search(item, title):
    pass

####################################################################################################
# def gen_next_page(key, params={}):
#     return 

def uL(text):
    return unicode(L(text))
