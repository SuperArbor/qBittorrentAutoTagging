import qbittorrentapi as qbit
import os, datetime, sys, re, copy
import yaml 

# 全部tag
TAGS_ALL = ['content', 'name', 'media', 'year', 'resolution', 'process_method', 'process_type', 'team']
# 合理的文件名分隔符
SPLITS = ['.', ' ']
# 压制组前缀
SPLIT_TEAM = '-'
EXTENTS = ['.mkv', '.mp4']
CONTENT_TYPES = ['Movie', 'TV']
MEDIA_TYPES_MORE = ['BluRay', 'Blu-ray', 'BDRip', 'DVD', 'DVDRip', 'HDDVD', 'HDTV', 'WEB', 'WEB-DL', 'WEBRip']
MEDIA_TYPES = ['BluRay', 'DVD', 'HDTV', 'WEB']
PROCESS_TYPES = ['Raw', 'Encode']
PROCESS_METHODS = ['x264', 'x265', 'H264', 'H265']
RESOLUTION_TYPES = ['720p', '1080p', '2160p']
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().year
UNKNOWN_TAG = '?'

def decode_torrent_tags(torrent_name:str, teams:list) -> dict:
    """Decode the torrent name for Movie or TV and returns tags

    Args:
        torrent_name (str): torrent name
        teams (list): teams in the buffer, used for some irregular torrent names

    Returns:
        dict: decoded tags
    """
    root, ext = os.path.splitext(torrent_name)
    if str.lower(ext) in EXTENTS:
        torrent_name = root
    split = ''
    groups = []
    for s in SPLITS:
        groups = torrent_name.split(s)
        if len(groups) >= 3:
            split = s
            break
    if not split:
        return {'content': ''}
    
    media = ''
    resolution = ''
    groups_lowered = [str.lower(group) for group in groups]
    # record the fields that have been handeled
    marked = []
    for media_type in MEDIA_TYPES_MORE:
        for i in range(len(groups_lowered)):
            if str.lower(media_type) == groups_lowered[i]:
                if groups_lowered[i] in [str.lower(mt) for mt in ['BluRay', 'Blu-ray', 'BDRip']]:
                    # including cases such as 'bluray', 'Bluray'
                    media = 'BluRay'
                elif groups_lowered[i] in [str.lower(mt) for mt in ['WEB', 'WEB-DL', 'WEBRip']]:
                    media = 'WEB'
                elif groups_lowered[i] in [str.lower(mt) for mt in ['DVD', 'HDDVD', 'DVDRip']]:
                    media = 'DVD'
                elif groups_lowered[i] in [str.lower(mt) for mt in ['HDTV']]:
                    media = 'HDTV'                
                else:
                    media = media_type
                marked.append(i)
                break
        if media:
            break
        
    if not media:
        # sometimes 'BluRay' is omitted when 'UHD' presents
        # 'UHD' and 'BluRay' can also both be included, thus handle this occation after 'BluRay' is failed to be detected
        for i in range(len(groups_lowered)):
            if i in marked:
                continue
            if groups_lowered[i] == 'uhd':
                media = 'BluRay'
                marked.append(i)
                break          
        
    for reso_type in RESOLUTION_TYPES:
        for i in range(len(groups_lowered)):
            if i in marked:
                continue
            if str.lower(reso_type) == groups_lowered[i]:
                resolution = reso_type
                marked.append(i)
                break
        if resolution:
            break
        
    if (not media) and (not resolution):
        return {'content': ''}
    
    last_item = groups.pop()
    last_items = last_item.split(SPLIT_TEAM)
    team = ''
    groups.extend(last_items)
    groups_lowered = [str.lower(group) for group in groups]
    if len(last_items) == 2:
        team = last_items[1]
        marked.append(len(groups) - 1)
    elif len(last_items) == 1:
        # sometimes the team is not prefixed with the splitter
        if last_item in teams:
            team = last_item
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
    content = ''
    for i in reversed(range(len(groups_lowered))):
        if year and content:
            break
        if i in marked:
            continue
        match = re.match(r's\d\d.*', groups_lowered[i], re.IGNORECASE)
        if match:
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
        
    if not content:
        content = 'Movie'
    
    marked.sort()
    name_idx = marked[0]
    name = ' '.join([groups[i] for i in range(name_idx)])
    tags = {'content': content, 'name':name, 'media':media, 'year':year, 
            'resolution':resolution, 'process_method':process_method, 'process_type':process_type, 
            'team': team}
    
    return tags

def handle_torrent(client, torrent:qbit.TorrentDictionary, 
                    trackers:dict, trackers_to_ignore:list,
                    tags_prefix:dict, tags_to_record:list, teams:list, 
                    overwrite:bool, update_tags:bool) -> tuple[str, dict]:
    """Setting category and tags of a torrent by decoding the torrent name

    Args:
        client (_type_): _description_
        torrent (qbit.TorrentDictionary): _description_
        trackers (dict): the mapping between categorys and tracker urls
        trackers_to_ignore (list): trackers to ignore
        tags_prefix (dict): prefixes for specified tag types
        tags_to_record (list): tag types to record
        teams (list): teams in buffer
        overwrite (bool): overwrite the existing tags when adding new ones
        update_tags (bool): update tags for torrent in the client

    Returns:
        tuple[str, dict]: the category and the tags
    """
    # get category
    category = ''
    for tracker in torrent.trackers:
        for cat, url in trackers.items():
            if str.lower(url) in str.lower(tracker.url):
                category = cat
                break
        if category:
            break
            
    if (not trackers_to_ignore) or (category not in trackers_to_ignore):
        # handle category
        if category:
            client.torrents_set_category(category, torrent_hashes=torrent.hash)
            print(f'category: {category}') 
        
        # handle tags
        tags = decode_torrent_tags(torrent.name, teams)
        if tags:
            tags_decorated = copy.copy(tags)
            for tag_key, tag_value in tags_decorated.items():
                if tag_key in tags_prefix.keys():
                    tags_decorated.update({tag_key:f'{tags_prefix[tag_key]}{tag_value}' if tag_value else ''})
            if update_tags:
                if overwrite:
                    client.torrents_remove_tags(torrent_hashes=torrent.hash)
                # consider tags_decorated = {'content': ''}, where tags such as 'media' are in tags_to_record but not in tags_decorated.keys()
                tags_needed = list({tag: tags_decorated[tag] for tag in tags_to_record if tag in tags_decorated.keys()}.values())
                client.torrents_add_tags(tags_needed, torrent_hashes=torrent.hash)
                print(f'tags: {tags_needed}')
        return category, tags    
    else:
        print(f'Category {category} in trackers_to_ignore list, skipping tagging for the torrent')
        return category, None

def process_new(info_hash:str, config:dict, statistics:dict):
    """Process a new torrent with its info hash 

    Args:
        info_hash (str): the info hash, used for retrieving the specific torrent from the client
    """
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 在tag前加上前缀以区分不同类型的tag
    tags_prefix = config['tags_prefix'] or {}
    # 记录的标签
    tags_to_record = config['tags_to_record'] or []
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers'] or []
    # 是否清除已有标签
    overwrite = config['overwrite'] or False
    # 是否更新客户端中的标签
    update_tags = config['update_tags'] or False
    # 需要过滤的trackers
    trackers_to_ignore = config['trackers_to_ignore'] or []
    # 全局统计
    statistics_total = statistics['TOTAL'] or {'team':{}}
    try:
        client.auth_log_in()
        categories_exist = client.torrent_categories.categories
        for cat in trackers.keys():
            if cat not in categories_exist:
                client.torrents_create_category(cat)
                
        print(f'Fetching specified torrent from the client...')        
        torrent_list = client.torrents_info(torrent_hashes=info_hash)
        if len(torrent_list) < 1:
            print(f'Torrent with hash {info_hash} unfound, skip it')
        else:
            torrent = torrent_list[0]
            print(f'Handling torrent {torrent.name}...')
            handle_torrent(
                client, torrent=torrent, trackers=trackers, trackers_to_ignore=trackers_to_ignore, 
                tags_prefix=tags_prefix, tags_to_record=tags_to_record, 
                teams=list(statistics_total['team'].keys()), overwrite=overwrite, update_tags=update_tags)
    except qbit.LoginFailed as e:
        print(e)
    client.auth_log_out()

def process_all(config:dict, statistics:dict) -> dict:
    """Process all the torrents in a client
    """
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 在tag前加上前缀以区分不同类型的tag
    tags_prefix = config['tags_prefix'] or {}
    # 记录的标签
    tags_to_record = config['tags_to_record'] or []
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers'] or []
    # 是否清除已有标签
    overwrite = config['overwrite'] or False
    # 是否更新statistics中的统计数据
    update_statistics = config['update_statistics'] or False
    # 是否更新客户端中的标签
    update_tags = config['update_tags'] or False
    # 需要过滤的trackers
    trackers_to_ignore = config['trackers_to_ignore'] or []
    # 全局统计
    statistics_total = statistics['TOTAL'] or {}
    # 分类统计
    statistics_categories = statistics['CATEGORIES'] or {}
    # 初始化统计数据
    for tag_type in tags_to_record:
        match str.lower(tag_type):
            case 'content':
                statistics_total.update({tag_type: {t: 0 for t in CONTENT_TYPES}})
            case 'media':
                statistics_total.update({tag_type: {t: 0 for t in MEDIA_TYPES}})
            case 'resolution':
                statistics_total.update({tag_type: {t: 0 for t in RESOLUTION_TYPES}})
            case 'team':
                if statistics_total.get(tag_type):
                    # teams in statistics are useful
                    statistics_total.update({tag_type: {t: 0 for t in statistics_total[tag_type].keys()}})
                else:
                    statistics_total.update({tag_type: {}})
            case 'process_type':
                statistics_total.update({tag_type: {t: 0 for t in PROCESS_TYPES}})
            case 'process_method':
                statistics_total.update({tag_type: {t: 0 for t in PROCESS_METHODS}})
            case 'year':
                statistics_total.update({tag_type: {}})
            case _:
                pass
                
    statistics_categories = {category: {} for category in trackers.keys() if category not in trackers_to_ignore}
    for category in statistics_categories.keys():
        for tag_type in tags_to_record:
            match str.lower(tag_type):
                case 'content':
                    statistics_categories[category].update({tag_type: {t: 0 for t in CONTENT_TYPES}})
                case 'media':
                    statistics_categories[category].update({tag_type: {t: 0 for t in MEDIA_TYPES}})
                case 'resolution':
                    statistics_categories[category].update({tag_type: {t: 0 for t in RESOLUTION_TYPES}})
                case 'team':
                    if statistics_categories[category].get(tag_type):
                        statistics_categories[category].update({tag_type: {t: 0 for t in statistics_total[tag_type].keys()}})
                    else:
                        statistics_categories[category].update({tag_type: {}})
                case 'process_type':
                    statistics_categories[category].update({tag_type: {t: 0 for t in PROCESS_TYPES}})
                case 'process_method':
                    statistics_categories[category].update({tag_type: {t: 0 for t in PROCESS_METHODS}})
                case 'year':
                    statistics_categories[category].update({tag_type: {}})
                case _:
                    pass
            
    try:
        client.auth_log_in()
        categories_exist = client.torrent_categories.categories
        for cat in trackers.keys():
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
            category, tags = handle_torrent(
                client, torrent=torrent, trackers=trackers, trackers_to_ignore=trackers_to_ignore,
                tags_prefix=tags_prefix, tags_to_record=tags_to_record, 
                teams=list(statistics_total['team'].keys()), overwrite=overwrite, update_tags=update_tags)
            if update_statistics and tags:
                for tag_type in tags.keys():
                    if not tag_type in tags_to_record:
                        continue
                    tag_entry = tags[tag_type] or UNKNOWN_TAG
                    if tag_entry in statistics_total[tag_type].keys():
                        statistics_total[tag_type][tag_entry] += 1
                    else:
                        statistics_total[tag_type][tag_entry] = 1
                    
                    if category:
                        if tag_entry in statistics_categories[category][tag_type].keys():
                            statistics_categories[category][tag_type][tag_entry] += 1
                        else:
                            statistics_categories[category][tag_type][tag_entry] = 1
    except qbit.LoginFailed as e:
        print(e)
    client.auth_log_out()
    return {'TOTAL': statistics_total, 'CATEGORIES': statistics_categories}

if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    path_config = os.path.join(current_dir, 'config.yaml')
    path_statistics = os.path.join(current_dir, 'statistics.yaml')
    
    if not os.path.exists(path_config):
        print(f'Config not found in path {path_config}, exiting...')
        exit(-1)
        
    if not os.path.exists(path_statistics):
        print(f'Statistics not found in path {path_statistics}, creating it...')
        with open(path_statistics, 'w', encoding='utf-8') as f:
            statistics = yaml.dump({'TOTAL':{}, 'CATEGORIES':{}}, f)
        
    with open(path_config, 'r', encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.Loader)
    
    with open(path_statistics, 'r', encoding='utf-8') as f:
        statistics = yaml.load(f, Loader=yaml.Loader)
        
    if len(sys.argv) == 1:
        print(f'Running process_all function with update_tags {"on" if config["update_tags"] else "off"} and update_statistics {"on" if config["update_statistics"] else "off"}')
        print(f'Handling all torrents...')
        statistics = process_all(config, statistics)
        
        if config['update_statistics']:
            print(f'Updating statistics...')
            with open(path_statistics, 'w', encoding='utf-8') as f:
                yaml.dump(statistics, f)
    else:
        info_hash = sys.argv[1]
        print(f'Running process_new function with update_tags {"on" if config["update_tags"] else "off"}')
        process_new(info_hash, config, statistics)
               