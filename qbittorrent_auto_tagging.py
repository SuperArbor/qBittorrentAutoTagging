import qbittorrentapi as qbit
import os, datetime, sys
import yaml 

# 全部tag
TAGS_ALL = ['content', 'name', 'media', 'year', 'resolution', 'process_method', 'process_type', 'team']
# 合理的文件名分隔符
SPLITS = ['.', ' ']
# 压制组前缀
SPLIT_TEAM = '-'
CONTENT_TYPES = ['Movie', 'TV']
MEDIA_TYPES = ['BluRay', 'Blu-ray', 'BDRip', 'DVD', 'DVDRip', 'HDDVD', 'HDTV', 'WEB', 'WEB-DL', 'WEBRip']
PROCESS_TYPES = ['Raw', 'Encode']
PROCESS_METHODS = ['x264', 'x265', 'H264', 'H265']
RESOLUTION_TYPES = ['720p', '1080p', '2160p']
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().year

def decode_torrent_tags(file_name:str, tags_prefix:dict) -> dict:
    # 解析文件名以生成tags
    split = ''
    groups = []
    for s in SPLITS:
        groups = file_name.split(s)
        if len(groups) >= 3:
            split = s
            break
    if not split:
        return None
    
    media = ''
    resolution = ''
    groups_lowered = [str.lower(group) for group in groups]
    marked = []
    for media_type in MEDIA_TYPES:
        for i in range(len(groups_lowered)):
            if str.lower(media_type) == groups_lowered[i]:
                if media_type in ['Blu-ray', 'BDRip']:
                    media_type = 'BluRay'
                elif media_type in ['WEB-DL', 'WEBRip']:
                    media_type = 'WEB'
                elif media_type in ['HDDVD', 'DVDRip']:
                    media_type = 'DVD'
                media = media_type
                marked.append(i)
                break
        if media:
            break    
        
    for reso_type in RESOLUTION_TYPES:
        for i in range(len(groups_lowered)):
            if str.lower(reso_type) == groups_lowered[i]:
                resolution = reso_type
                marked.append(i)
                break
        if resolution:
            break
        
    if (not media) and (not resolution):
        return None
    
    last_item = groups.pop()
    last_items = last_item.split(SPLIT_TEAM)
    team = ''
    groups.extend(last_items)
    groups_lowered = [str.lower(group) for group in groups]
    if len(last_items) == 2:
        team = last_items[1]
        marked.append(len(groups) - 1)
        
    process_method = ''
    process_type = ''
    for method in PROCESS_METHODS:
        for i in range(len(groups_lowered)):
            if i in marked:
                continue
            if str.lower(method) == groups_lowered[i]:  
                process_method = method
                if method.startswith('x26'):
                    process_type = 'Encode'
                elif method.startswith('H26'):
                    process_type = 'Raw'
                marked.append(i)
                break
        if process_method:
            break
    
    year = ''
    content = 'Movie'
    for i in reversed(range(len(groups_lowered))):
        if year and content:
            break
        if i in marked:
            continue
        if groups_lowered[i].startswith('s0'):
            content = 'TV'
            marked.append(i)
            continue
        try:
            if YEAR_MIN <= int(groups[i]) <= YEAR_MAX:
                year = groups[i]
                marked.append(i)
                continue
        except:
            pass
    
    marked.sort()
    name_idx = marked[0]
    name = ' '.join([groups[i] for i in range(name_idx)])
    tags = {'content': content, 'name':name, 'media':media, 'year':year, 
            'resolution':resolution, 'process_method':process_method, 'process_type':process_type, 
            'team': team}
    for tag_key, tag_value in tags.items():
        if tag_key in tags_prefix.keys():
            tags.update({tag_key:f'{tags_prefix[tag_key]}{tag_value}' if tag_value else ''})
    return tags

def handle_torrrent(client, torrent:qbit.TorrentDictionary, 
                    trackers:dict, trackers_for_tagging:list,
                    tags_prefix:dict, tags_to_record:list, overwrite:bool):
    # handle category
    category = ''
    for tracker in torrent.trackers:
        for cat, url in trackers.items():
            if str.lower(url) in str.lower(tracker.url):
                category = cat
                break
        if category:
            break
    if category:
        client.torrents_set_category(category, torrent_hashes=[torrent.hash])
        print(f'category: {category}') 
            
    # handle tags
    if category in trackers_for_tagging:
        tags = decode_torrent_tags(torrent.name, tags_prefix)
        if tags:
            tags_needed = {label: tags[label] for label in tags_to_record}.values()
            if overwrite:
                client.torrents_remove_tags(torrent_hashes=[torrent.hash])
            client.torrents_add_tags(tags_needed, torrent_hashes=[torrent.hash])
            print(f'tags: {tags}')

def process_new(info_hash:str):
    current_dir = os.path.dirname(__file__)
    with open(os.path.join(current_dir, 'config.yaml'), 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.Loader)
        
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 在tag前加上前缀以区分不同类型的tag
    tags_prefix = config['tags_prefix']
    # 记录的标签
    tags_to_record = config['tags_to_record']
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers']
    # 是否清除已有标签
    overwrite = config['overwrite']
    # 需要打标的trackers
    trackers_for_tagging = config['trackers_for_tagging'] if config['trackers_for_tagging'] else list(trackers.keys())
    try:
        client.auth_log_in()
        categories_exist = client.torrent_categories.categories
        for cat, url in trackers.items():
            if cat not in categories_exist:
                client.torrents_create_category(cat)
                
        print(f'Fetching all the torrents from the client...')        
        torrent_list = client.torrents_info()
        print(f'Done. {len(torrent_list)} torrents to match.')        
        torrents_found = [t for t in torrent_list if t.info.hash == info_hash]
        if len(torrents_found) < 1:
            print(f'Torrent with hash {info_hash} unfound, skip it')
        else:
            torrent = torrents_found[0]
            print(f'Handling torrent {torrent.name}...')
            handle_torrrent(client, torrent=torrent, trackers=trackers, trackers_for_tagging=trackers_for_tagging, 
                            tags_prefix=tags_prefix, tags_to_record=tags_to_record, overwrite=overwrite)
    except qbit.LoginFailed as e:
        print(e)
    client.auth_log_out()

def process_all():
    current_dir = os.path.dirname(__file__)
    with open(os.path.join(current_dir, 'config.yaml'), 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.Loader)
        
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 在tag前加上前缀以区分不同类型的tag
    tags_prefix = config['tags_prefix']
    # 记录的标签
    tags_to_record = config['tags_to_record']
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers']
    # 是否清除已有标签
    overwrite = config['overwrite']
    # 需要打标的trackers
    trackers_for_tagging = config['trackers_for_tagging'] if config['trackers_for_tagging'] else list(trackers.keys())
    try:
        client.auth_log_in()
        categories_exist = client.torrent_categories.categories
        for cat, url in trackers.items():
            if cat not in categories_exist:
                client.torrents_create_category(cat)
        
        print(f'Fetching all the torrents from the client...')        
        torrent_list = client.torrents_info()
        total = len(torrent_list)
        print(f'Done. {total} torrents to process.')        
        count = 0
        for torrent in torrent_list:
            count += 1
            print(f'({count} / {total}) Handling torrent {torrent.name}...')
            handle_torrrent(client, torrent=torrent, trackers=trackers, trackers_for_tagging=trackers_for_tagging,
                            tags_prefix=tags_prefix,  tags_to_record=tags_to_record, overwrite=overwrite)
    except qbit.LoginFailed as e:
        print(e)
    client.auth_log_out()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        process_all()
    else:
        info_hash = sys.argv[1]
        process_new(info_hash)
               