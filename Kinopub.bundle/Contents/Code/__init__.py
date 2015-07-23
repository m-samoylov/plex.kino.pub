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

ITEM_URL = kinopub_api.API_URL + '/items'
ITEMS_PER_PAGE = 19

####################################################################################################
def Start():
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
                key     = Callback(Search, qp={}),
                title   = unicode('Поиск'),
                prompt  = unicode('Поиск')
            ),
            DirectoryObject(
                key = Callback(Items, title='Последние', qp={}),
                title = unicode('Последние'),
                summary = unicode('Все фильмы и сериалы отсортированные по дате добавления/обновления.')
            )
        ]
    )

    response = kpubapi.api_request('types')
    if response['status'] == 200:
        for item in response['items']:
            li = DirectoryObject(
                key = Callback(Types, title=item['title'], qp={'type': item['id']}),
                title = unicode(item['title']),
                summary = unicode(item['title'])
            )
            oc.add(li)
    else:
        return MessageContainer("Ошибка %s" % response['status'], response['message'])
    return oc
'''
  Next screen after MainMenu.
  Show folders:
    - Search
    - Latest (sort by date/update)
    - Rating (sort by rating)
    - Genres
'''
@route(PREFIX + '/Types', qp=dict)
def Types(title, qp=dict):
    oc = ObjectContainer(
        view_group = 'InfoList',
        objects = [
            InputDirectoryObject(
                key     = Callback(Search, qp=qp),
                title   = unicode('Поиск'),
                prompt  = unicode('Поиск')
            ),
            DirectoryObject(
                key = Callback(Items, title='Последние', qp=merge_dicts(qp, dict({'sort': 'updated-'}))),
                title = unicode('Последние'),
                summary = unicode('Отсортированные по дате добавления/обновления.')
            ),
            DirectoryObject(
                key = Callback(Items, title='Популярные', qp=merge_dicts(qp, dict({'sort': 'rating-'}))),
                title = unicode('Популярные'),
                summary = unicode('Отсортированные по рейтингу')
            ),
            DirectoryObject(
                key = Callback(Genres, title='Жанры', qp=qp),
                title = unicode('Жанры'),
                summary = unicode('Список жанров')
            ),
        ]
    )
    return oc

'''
  Called from Types route.
  Display genres for media type
'''
@route(PREFIX + '/Genres', qp=dict)
def Genres(title, qp=dict):
    response = kpubapi.api_request('genres', params={'type': qp['type']})
    oc = ObjectContainer(view_group='InfoList')
    if response['status'] == 200:
        for genre in response['items']:
            li = DirectoryObject(
                key = Callback(Items, title=genre['title'], qp={'type':qp['type'], 'genre': genre['id']}),
                title = genre['title'],
            )
            oc.add(li)
    return oc

'''
  Shows media items.
  Items are filtered by 'qp' param.
  See http://kino.pub/docs/api/v2/api.html#video
'''
@route(PREFIX + '/Items', qp=dict)
def Items(title, qp=dict):
    qp['perpage'] = ITEMS_PER_PAGE
    response = kpubapi.api_request('items', qp)
    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
    if response['status'] == 200:
        video_clips = {}
        @parallelize
        def load_items():
            for num in xrange(len(response['items'])):
                item = response['items'][num]

                @task
                def load_task(num=num, item=item, video_clips=video_clips):
                    response2 = kpubapi.api_request('items/%s' % item['id'])
                    if response2['status'] == 200:
                        videos = response2['item'].get('videos', [])
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
                                duration = int(videos[0]['duration'])*1000,
                                thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                            )
                            
                        else:
                            # create directory for seasons and multiseries videos
                            li = DirectoryObject(
                                key = Callback(View, title=item['title'], qp={'id': item['id']}),
                                title = item['title'],
                                summary = item['plot'],
                                thumb = Resource.ContentsOfURLWithFallback(item['posters']['medium'], fallback=R(ICON))
                            )
                        video_clips[num] = li

        for key in sorted(video_clips):
            oc.add(video_clips[key])

        # Add "next page" button
        pagination = response['pagination']
        if (int(pagination['current'])) + 1 <= int(pagination['total']):
            qp['page'] = int(pagination['current'])+1
            li = NextPageObject(
                key = Callback(Items, title=title, qp=qp),
                title = unicode('Еще...')
            )
            oc.add(li)
    return oc

'''
  Display serials or multi series movies
'''
@route(PREFIX + '/View', qp=dict)
def View(title, qp=dict):
    response = kpubapi.api_request('items/%s' % int(qp['id']))
    oc = ObjectContainer(title2=unicode(title), view_group='InfoList')
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
                            episode_title = "%s" % episode['title'] if len(episode['title']) > 1 else "Эпизод %s" % episode_number
                            episode_title = "%02d. %s"  % (episode_number, episode_title)
                            li = VideoClipObject(
                                url = "%s/%s?access_token=%s#season=%s&episode=%s" % (ITEM_URL, item['id'], settings.get('access_token'), season['number'], episode_number),
                                title = unicode(episode_title),
                                year = int(item['year']),
                                summary = str(item['plot']),
                                genres = [x['title'] for x in item['genres']],
                                directors = item['director'].split(','),
                                countries = [x['title'] for x in item['countries']],
                                content_rating = item['rating'],
                                duration = int(episode['duration'])*1000,
                                thumb = Resource.ContentsOfURLWithFallback(episode['thumbnail'], fallback=R(ICON))
                            )
                            oc.add(li)
                        break
            else:
                for season in item['seasons']:
                    season_title = season['title'] if len(season['title']) > 2 else "Сезон %s" % int(season['number'])
                    test_url = item['posters']['medium']
                    li = DirectoryObject(
                        key = Callback(View, title=season_title, qp={'id': item['id'], 'season': season['number']}),
                        title = unicode(season_title),
                        tagline = item['title'],
                        summary = item['title'],
                        art = Resource.ContentsOfURLWithFallback(test_url, fallback=R(ART)),
                        thumb = Resource.ContentsOfURLWithFallback(season['episodes'][0]['thumbnail'].replace('dev.',''), fallback=R(ICON))
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
                    year = int(item['year']),
                    summary = str(item['plot']),
                    genres = [x['title'] for x in item['genres']],
                    directors = item['director'].split(','),
                    countries = [x['title'] for x in item['countries']],
                    content_rating = item['rating'],
                    thumb = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON)),
                    art = Resource.ContentsOfURLWithFallback(video['thumbnail'], fallback=R(ICON))
                )
                oc.add(li)
        else:
            # In true behaviour this section will never reached
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
            oc.add(li)
    return oc

'''
  Search items
'''
@route(PREFIX + '/Search', qp=dict)
def Search(query, qp=dict):
    if qp.get('id'):
        del qp['id']

    return Items('Поиск', qp=merge_dicts(qp, dict({'title' : query, 'perpage': ITEMS_PER_PAGE})))

####################
def merge_dicts(*args):
    result = {}
    for d in args:
        result.update(d)
    return result