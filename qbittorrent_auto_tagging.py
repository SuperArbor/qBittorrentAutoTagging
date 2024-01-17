import qbittorrentapi as qbit
import os, datetime, sys, re, copy
import yaml 

# 合理的文件名分隔符
SPLITTERS = ['.', ' ']
# 压制组前缀
SPLITTER_TEAM = '-'
EXTENTS = ['.mkv', '.mp4']
MEDIA_TYPES_MORE = ['BluRay', 'Blu-ray', 'BDRip', 'DVD', 'DVDRip', 'HDDVD', 'HDTV', 'WEB', 'WEB-DL', 'WEBRip']
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().year
UNKNOWN_TAG = '?'

# 全部tag
TAGS = {
    'content': ['Movie', 'TV'],
    'media': ['BluRay', 'WEB', 'DVD', 'HDTV'],
    'process_type': ['Encode', 'Raw'],
    'process_method': ['x264', 'x265', 'H.264', 'H.265', 'XviD', 'DivX', 'MPEG-2'],
    'resolution': ['1080', '2160', '720']
}

def decode_torrent_tags(torrent_name:str, teams:list=[], tag_types:list=[]) -> dict:
    """Decode the torrent name for Movie or TV and returns tags

    Args:
        torrent_name (str): torrent name
        teams (list): teams in the buffer, used for some irregular torrent names
        tag_types (list): tag types specified to decode

    Returns:
        dict: decoded tags
    """
    root, ext = os.path.splitext(torrent_name)
    if str.lower(ext) in EXTENTS:
        torrent_name = root
    splitter = ''
    current_best = 0
    min_groups = 3
    for s in SPLITTERS:
        # 选取能够获得最多分组的分隔符
        groups_test = torrent_name.split(s)
        if len(groups_test) >= max(min_groups, current_best):
            current_best = len(groups_test)
            splitter = s
    if not splitter:
        return {'content': ''}
    groups = torrent_name.split(splitter)
    
    if not tag_types:
        tag_types = ['content', 'name', 'media', 'year', 'resolution', 'process_method', 'process_type', 'team']
    
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
        
    for reso_type in TAGS['resolution']:
        for i in range(len(groups_lowered)):
            if i in marked:
                continue
            if re.match(reso_type + r'[pi]', groups_lowered[i]):
                resolution = groups_lowered[i]
                marked.append(i)
                break
        if resolution:
            break
        
    if (not media) and (not resolution):
        return {'content': ''}
    
    # Handling team
    team = ''
    if 'team' in tag_types:
        last_item = groups.pop()
        last_items = last_item.split(SPLITTER_TEAM)
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
        
    # Handling process_method and process_type
    process_method = ''
    process_type = ''
    if 'process_method' in tag_types or 'process_type' in tag_types:
        for i in range(len(groups_lowered)):
            if i in marked:
                continue
            mat = re.match(r'(x26\d)|(h\.?26\d)|(avc)|(hevc)|(xvid)|(divx)|(mpeg-2)', groups_lowered[i], re.IGNORECASE)
            if mat:
                r = str.lower(mat.string)
                if r.startswith('x26'):
                    process_method = r
                    process_type = 'Encode'
                elif r.startswith('h26') or r.startswith('h.26'):
                    process_method = str.upper(r)
                    process_type = 'Raw'
                elif r == 'avc':
                    process_method = 'H.264'
                    process_type = 'Raw'
                elif r == 'hevc':
                    process_method = 'H.265'
                    process_type = 'Raw'
                elif r == 'xvid':
                    process_method = 'XviD'
                    process_type = 'Encode'
                elif r == 'divx':
                    process_method = 'DivX'
                    process_type = 'Encode'
                elif r == 'mpeg-2':
                    process_method = 'MPEG-2'
                    process_type = 'Raw'
                else:
                    process_method = r
                    process_type = 'Encode'
                marked.append(i)
                break
    
    # Handling year and content
    year = ''
    content = ''
    if 'year' in tag_types or 'content' in tag_types or 'year' in tag_types:
        # 'year' must be decoded if 'name' is to be decoded since 'year' is mostly next to 'name'
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
    
    name = ''
    if 'name' in tag_types:
        marked.sort()
        name_idx = marked[0]
        name = ' '.join([groups[i] for i in range(name_idx)])

    tags = {}
    for tag_type in tag_types:
        tags.update({tag_type: eval(tag_type)})
    
    return tags

def handle_torrent_tags(torrent:qbit.TorrentDictionary, tags_to_record:dict, tags_to_reserve:list, teams:list, 
                    overwrite:bool, update_tags:bool, delay_operation:bool=False) -> tuple[dict, dict]:
    """Setting tags of a torrent by decoding the torrent name

    Args:
        torrent (qbit.TorrentDictionary): the torrent to be handled
        tags_to_record (dict): tag types to record
        tags_to_reserve (list): tags to be reserved when clearing old tags
        teams (list): teams in buffer
        overwrite (bool): overwrite the existing tags when adding new ones
        update_tags (bool): update tags for torrent in the client
        delay_operation (bool): delay tagging operation, only return category and tags

    Returns:
        tuple[dict, dict]: the tags and the tags to be shown in the client UI (with prefixes)
    """
    # handle tags
    tags = decode_torrent_tags(torrent.name, teams=teams, tag_types=list(tags_to_record.keys()))
    if tags:
        tags_UI = copy.copy(tags)
        for tag_type, tag_value in tags_UI.items():
            tags_UI.update({tag_type:f'{tags_to_record[tag_type]["prefix"]}{tag_value}' if tag_value else ''})            
        if update_tags and not delay_operation:
            if overwrite:
                # 保留tags_to_reserve中的标签
                current_tags = [t.strip() for t in torrent['tags'].split(',')]
                torrent.remove_tags([t for t in current_tags if t not in tags_to_reserve])
            t_tags_list = tags_UI.values()
            if t_tags_list:
                torrent.add_tags(t_tags_list)
            print(f'tags: {t_tags_list}')
            
        return tags, tags_UI
    else:
        return {}, {}    

def process_new(info_hash:str, config:dict, statistics:dict):
    """Process a new torrent with its info hash 

    Args:
        info_hash (str): the info hash, used for retrieving the specific torrent from the client
    """
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 记录的标签
    tags_to_record = config['tags_to_record'] or {}
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers'] or []
    # 是否清除已有标签
    overwrite = config['overwrite'] or False
    # 更新标签时保留的标签内容
    tags_to_reserve = config['tags_to_reserve'] or []
    # 是否更新客户端中的标签
    update_tags = config['update_tags'] or False
    # 需要过滤的trackers
    trackers_to_ignore = config['trackers_to_ignore'] or []
    # 全局统计
    statistics_total = statistics['TOTAL'] or {'team':{}}
    try:
        client.auth_log_in()
                
        print(f'Fetching specified torrent from the client...')        
        torrent_list = client.torrents_info(torrent_hashes=info_hash)
        if len(torrent_list) < 1:
            print(f'Torrent with hash {info_hash} unfound, skip it')
        else:
            torrent = torrent_list[0]
            
            # get category
            category = ''
            for tracker in torrent.trackers:
                for cat, url in trackers.items():
                    if str.lower(url) in str.lower(tracker.url):
                        category = cat
                        break
                if category:
                    # check and create category
                    if category not in client.torrent_categories.categories:
                        client.torrents_create_category(category)
                    break
            # handle category
            if category:
                if torrent['category'] != category:
                    torrent.set_category(category)
                print(f'category: {category}')     
                
            if (not trackers_to_ignore) or (category not in trackers_to_ignore):
                print(f'Handling tags for torrent {torrent.name}...')
                handle_torrent_tags(torrent=torrent, tags_to_record=tags_to_record, tags_to_reserve=tags_to_reserve, 
                    teams=list(statistics_total['team'].keys()), overwrite=overwrite, update_tags=update_tags, delay_operation=False)
            else:
                print(f'Torrent {torrent.name} in trackers_to_ignore, skip tagging it')
    except qbit.LoginFailed as e:
        print(e)
    client.auth_log_out()

def process_all(config:dict, statistics:dict) -> dict:
    """Process all the torrents in a client

    Args:
        config (dict): configuration
        statistics (dict): statistics read from a file

    Returns:
        dict: the updated statistics
    """
    host, port, username, password = config['host'], config['port'], config['username'], config['password']
    conn_info = dict(host=host, port=port, username=username, password=password,)
    client = qbit.Client(**conn_info)

    # 记录的标签
    tags_to_record = config['tags_to_record'] or {}
    # 服务器缩写：url关键词，用于创建种子的categories
    trackers = config['trackers'] or []
    # 是否清除已有标签
    overwrite = config['overwrite'] or False
    # 更新标签时保留的标签内容
    tags_to_reserve = config['tags_to_reserve'] or []
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
    for tag_type in tags_to_record.keys():
        if tag_type == 'team':
            if statistics_total.get(tag_type):
                # teams in statistics are useful
                statistics_total.update({tag_type: {t: 0 for t in statistics_total[tag_type].keys()}})
            else:
                statistics_total.update({tag_type: {}})
            
            for category in statistics_categories.keys():
                if statistics_categories[category].get(tag_type):
                    statistics_categories[category].update({tag_type: {t: 0 for t in statistics_total[tag_type].keys()}})
                else:
                    statistics_categories[category].update({tag_type: {}})
        elif tag_type == 'year':
            statistics_total.update({tag_type: {}})   
            
            for category in statistics_categories.keys():
                statistics_categories[category].update({tag_type: {}})
        else:
            statistics_total.update({tag_type: {t: 0 for t in TAGS[tag_type]}})
            for category in statistics_categories.keys():
                statistics_categories[category].update({tag_type: {t: 0 for t in TAGS[tag_type]}})
    
    # 清除文件中的陈旧标签
    for tag_type in statistics_total.keys():
        if (tag_type not in tags_to_record.keys()) and tag_type != 'team':
            statistics_total[tag_type] = {}        
    for category in statistics_categories.keys():
        for tag_type in statistics_categories[category].keys():
            if (tag_type not in tags_to_record.keys()) and tag_type != 'team':
                statistics_categories[category][tag_type] = {}
    
    # tags_to_record中存在任意标签类型需要限制标签显示数目时，采用delay_operation
    delay_operation = False
    for tag_type in tags_to_record.keys():
        if tags_to_record[tag_type]['max_number'] > 0:
            delay_operation = True
            break       
    if delay_operation:
        print(f'Running with delay operation mode')
    else:
        print(f'Running without delay operation mode')
        
    try:
        client.auth_log_in()
        
        # check and create categories
        for cat in trackers.keys():
            if cat not in client.torrent_categories.categories:
                client.torrents_create_category(cat)
        
        print(f'Fetching all the torrents from the client...')        
        torrent_list = client.torrents_info()
        total = len(torrent_list)
        print(f'Done. {total} torrents to process.')     
           
        count = 0
        torrent_tags = {}
        for torrent in torrent_list:
            count += 1
            
            # get category
            category = ''
            for tracker in torrent.trackers:
                for cat, url in trackers.items():
                    if str.lower(url) in str.lower(tracker.url):
                        category = cat
                        break
                if category:
                    break
            
            # handle category
            if category:
                if torrent['category'] != category:
                    torrent.set_category(category)
                print(f'category: {category}') 
            
            if (not trackers_to_ignore) or (category not in trackers_to_ignore):
                if delay_operation:
                    print(f'({count} / {total}) [Delayed] Handling tags for torrent {torrent.name}...')
                else:
                    print(f'({count} / {total}) Handling tags for torrent {torrent.name}...')
                    
                tags, tags_UI = handle_torrent_tags(torrent=torrent, tags_to_record=tags_to_record, tags_to_reserve=tags_to_reserve, 
                    teams=list(statistics_total['team'].keys()), overwrite=overwrite, update_tags=update_tags, delay_operation=delay_operation)
                # torrent_tags is used to update client UI, so tags_UI is passed in
                if delay_operation:
                    torrent_tags.update({torrent.hash: tags_UI if tags_UI else {}})
                if update_statistics and category:
                    # create entries for the category in statistics if not existing
                    if category not in statistics_categories.keys():
                        statistics_categories[category] = {tag_type:{} for tag_type in tags_to_record.keys()}
                if update_statistics and tags:
                    # store unprefixed tags in statistics
                    for tag_type in tags.keys():
                        tag_value = tags[tag_type] or UNKNOWN_TAG
                        if tag_value in statistics_total[tag_type].keys():
                            statistics_total[tag_type][tag_value] += 1
                        else:
                            statistics_total[tag_type][tag_value] = 1
                        
                        if category:
                            if tag_value in statistics_categories[category][tag_type].keys():
                                statistics_categories[category][tag_type][tag_value] += 1
                            else:
                                statistics_categories[category][tag_type][tag_value] = 1
            else:
                print(f'({count} / {total}) Torrent {torrent.name} in trackers_to_ignore, skip tagging it')
        
        if update_tags:
            if delay_operation:
                print(f'Delay operation starts: updating tags...')
                # remove tags with too few entries
                # stores tag type - tag list pairs (the tags are prefixed) such as {'media': ['$BluRay', '$DVD', '$WEB']}
                tagType_tags = {tag_type:set() for tag_type in tags_to_record.keys()}
                # stores tag - number pairs where the number is the torrent number with the tag, such as {‘#Movie’: 2011}
                tag_numbers = {}
                # stores tags that should be removed
                tags_to_remove = []
                for t_tags in torrent_tags.values():
                    # obtain tagType_tags and tag_numbers in this loop
                    for tag_type, tag in t_tags.items():
                        tag_numbers[tag] = 1 if tag not in tag_numbers.keys() else tag_numbers[tag] + 1
                        tagType_tags[tag_type].add(tag)
                
                for tag_type in tagType_tags.keys():
                    # obtain tags_to_remove list
                    tags_of_type = list(tagType_tags[tag_type])
                    tags_limit_of_type = tags_to_record[tag_type]['max_number']
                    if tags_limit_of_type > 0 and tags_limit_of_type < len(tags_of_type):
                        tags_of_type.sort(key=lambda x: tag_numbers[x], reverse=True)
                        tags_to_remove.extend(tags_of_type[tags_limit_of_type: -1])
                
                # 保留tags_to_reserve中的标签
                tags_to_remove = [t for t in tags_to_remove if t not in tags_to_reserve]
                count = 0
                total = len(torrent_tags)
                for t_hash, t_tags in torrent_tags.items():
                    count += 1
                    torrent = client.torrents_info(torrent_hashes=t_hash)[0]
                    print(f'({count} / {total}) Tagging torrent {torrent.name}...')
                    t_tags_list = [t for t in t_tags.values() if t not in tags_to_remove]
                    if overwrite:
                        # 保留tags_to_reserve中的标签
                        current_tags = [t.strip() for t in torrent['tags'].split(',')]
                        torrent.remove_tags([t for t in current_tags if t not in tags_to_reserve])
                    if t_tags_list:
                        torrent.add_tags(t_tags_list)
                        print(f'tags: {t_tags_list}')
            
            print(f'Remove unneeded tags (those used by no torrents)..')
            tags_to_delete = []
            for tag in client.torrents_tags():
                torrent_list = client.torrents_info(tag=tag)
                if len(torrent_list) == 0:
                    tags_to_delete.append(tag)
            
            client.torrents_delete_tags(tags=tags_to_delete)
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
            # remove tag types with zero entries
            statistics_ = {'TOTAL':{}, 'CATEGORIES':{}}
            for tag_type in statistics['TOTAL'].keys():
                if statistics['TOTAL'][tag_type].values():
                    statistics_['TOTAL'][tag_type] = {}
                    keep_tag_type = False
                    for tag in statistics['TOTAL'][tag_type].keys():
                        if statistics['TOTAL'][tag_type][tag] > 0:
                            statistics_['TOTAL'][tag_type][tag] = statistics['TOTAL'][tag_type][tag]
                            keep_tag_type = True
                    if not keep_tag_type:
                        statistics_['TOTAL'].pop(tag_type)
            
            # remove categories with zero entries
            for category in statistics['CATEGORIES'].keys():
                keep_category = False           
                if  statistics['CATEGORIES'][category].values():
                    statistics_['CATEGORIES'][category] = {}
                    # remove tag types with zero entries
                    for tag_type in statistics['CATEGORIES'][category].keys():
                        if statistics['CATEGORIES'][category][tag_type].values():
                            statistics_['CATEGORIES'][category][tag_type]= {}
                            keep_tag_type = False
                            for tag in statistics['CATEGORIES'][category][tag_type].keys():
                                if statistics['CATEGORIES'][category][tag_type][tag] > 0:
                                    statistics_['CATEGORIES'][category][tag_type][tag] = statistics['CATEGORIES'][category][tag_type][tag]
                                    keep_tag_type = True
                                    keep_category = True
                            if not keep_tag_type:
                                statistics_['CATEGORIES'][category].pop(tag_type)
                if not keep_category:
                    statistics_['CATEGORIES'].pop(category)
            
            with open(path_statistics, 'w', encoding='utf-8') as f:
                yaml.dump(statistics_, f)
    else:
        info_hash = sys.argv[1]
        print(f'Running process_new function with update_tags {"on" if config["update_tags"] else "off"}')
        process_new(info_hash, config, statistics)
               