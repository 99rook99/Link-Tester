"""
    Link Tester XBMC Addon
    Copyright (C) 2015 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import urlresolver
import xbmcgui
import xbmcplugin
import sys
import os.path
from url_dispatcher import URL_Dispatcher
import log_utils
import kodi

def __enum(**enums):
    return type('Enum', (), enums)

LINK_PATH = os.path.join(kodi.translate_path(kodi.get_profile()), 'links.txt')
MODES = __enum(
    MAIN='main', ADD_LINK='add_link', PLAY_LINK='play_link', DELETE_LINK='delete_link', SETTINGS='settings', EDIT_LINK='edit_link'
)

url_dispatcher = URL_Dispatcher()

@url_dispatcher.register(MODES.MAIN)
def main_menu():
    kodi.create_item({'mode': MODES.ADD_LINK}, 'Add Link', is_folder=False, is_playable=False)
    kodi.create_item({'mode': MODES.SETTINGS}, 'URLResolver Settings', is_folder=False, is_playable=False)
    if os.path.exists(LINK_PATH):
        with open(LINK_PATH) as f:
            for i, line in enumerate(f):
                item = line.split('|')
                link = item[0].strip()
                if not link: continue
                try:
                    label = item[1]
                except:
                    label = item[0]
                queries = {'mode': MODES.DELETE_LINK, 'index': i}
                menu_items = [('Delete Link', 'RunPlugin(%s)' % (kodi.get_plugin_url(queries))), ]
                queries = {'mode': MODES.EDIT_LINK, 'index': i}
                menu_items.append(('Edit Link', 'RunPlugin(%s)' % (kodi.get_plugin_url(queries))),)
                kodi.create_item({'mode': MODES.PLAY_LINK, 'link': link}, label, is_folder=False, is_playable=True, menu_items=menu_items)
    
    kodi.set_content('files')
    kodi.end_of_directory(cache_to_disc=False)

@url_dispatcher.register(MODES.ADD_LINK, [], ['link', 'name', 'refresh'])
def add_link(link=None, name=None, refresh=True):
    if link is None:
        result = prompt_for_link()
    else:
        if name is None:
            result = (link, )
        else:
            result = (link, name)
            
    if result:
        if not os.path.exists(os.path.dirname(LINK_PATH)):
            os.mkdir(os.path.dirname(LINK_PATH))
            
        with open(LINK_PATH, 'a') as f:
            line = '|'.join(result)
            if not line.endswith('\n'):
                line += '\n'
            f.write(line)
        
        if refresh:
            kodi.refresh_container()

@url_dispatcher.register(MODES.SETTINGS)
def urlresolver_settings():
    urlresolver.display_settings()
    
@url_dispatcher.register(MODES.DELETE_LINK, ['index'])
def delete_link(index):
    new_lines = []
    with open(LINK_PATH) as f:
        for i, line in enumerate(f):
            if i == int(index):
                continue
            new_lines.append(line)
            
    with open(LINK_PATH, 'w') as f:
        for line in new_lines:
            f.write(line)

    kodi.refresh_container()

@url_dispatcher.register(MODES.EDIT_LINK, ['index'])
def edit_link(index):
    new_lines = []
    with open(LINK_PATH) as f:
        for i, line in enumerate(f):
            if i == int(index):
                item = line.split('|')
                result = prompt_for_link(*item)
                if result:
                    line = '|'.join(result)
                
            new_lines.append(line)

    with open(LINK_PATH, 'w') as f:
        for line in new_lines:
            if not line.endswith('\n'):
                line += '\n'
                
            f.write(line)

    kodi.refresh_container()

def prompt_for_link(old_link='', old_name=''):
    if old_link.endswith('\n'): old_link = old_link[:-1]
    if old_name.endswith('\n'): old_name = old_name[:-1]
    new_link = kodi.get_keyboard('Edit Link', old_link)
    if new_link is None:
        return

    new_name = kodi.get_keyboard('Enter Name', old_name)
    if new_name is None:
        return
    
    if new_name:
        return (new_link, new_name)
    else:
        return (new_link, )
    
@url_dispatcher.register(MODES.PLAY_LINK, ['link'])
def play_link(link):
    log_utils.log('Playing Link: |%s|' % (link), log_utils.LOGDEBUG)
    hmf = urlresolver.HostedMediaFile(url=link)
    if not hmf:
        log_utils.log('Indirect hoster_url not supported by urlresolver: %s' % (link))
        kodi.notify('Link Not Supported: %s' % (link), duration=7500)
        return False
    log_utils.log('Link Supported: |%s|' % (link), log_utils.LOGDEBUG)

    try:
        stream_url = hmf.resolve()
        if not stream_url or not isinstance(stream_url, basestring):
            try: msg = stream_url.msg
            except: msg = link
            raise Exception(msg)
    except Exception as e:
        try: msg = str(e)
        except: msg = link
        kodi.notify('Resolve Failed: %s' % (msg), duration=7500)
        return False
        
    log_utils.log('Link Resolved: |%s|%s|' % (link, stream_url), log_utils.LOGDEBUG)
        
    listitem = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem)

def main(argv=None):
    if sys.argv: argv = sys.argv
    queries = kodi.parse_query(sys.argv[2])
    log_utils.log('Version: |%s| Queries: |%s|' % (kodi.get_version(), queries))
    log_utils.log('Args: |%s|' % (argv))

    # don't process params that don't match our url exactly. (e.g. plugin://plugin.video.1channel/extrafanart)
    plugin_url = 'plugin://%s/' % (kodi.get_id())
    if argv[0] != plugin_url:
        return

    mode = queries.get('mode', None)
    url_dispatcher.dispatch(mode, queries)

if __name__ == '__main__':
    sys.exit(main())
