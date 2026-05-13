"""
Complete parser for AggSearchV6Response — extracts all search suggest results with stats.
API: POST /search/v6/agg-search?X-ENC=pb (scene="suggest" for autocomplete)
"""
import json, sys

def read_varint(data, offset):
    value = 0; shift = 0
    while offset < len(data):
        byte = data[offset]; value |= (byte & 0x7F) << shift; offset += 1
        if not (byte & 0x80): break
        shift += 7
    return value, offset

def read_ld(data, offset):
    length, offset = read_varint(data, offset)
    return data[offset:offset + length], offset + length

def parse_list_app_card(data):
    """Return {title, pkg, app_id} from ListAppCard."""
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 1: result['app_id'] = v
        elif wt == 2:
            r, off = read_ld(data, off)
            if t == 2:
                try: result['package_name'] = r.decode('utf-8')
                except: pass
            elif t == 5:
                try: result['title'] = r.decode('utf-8')
                except: pass
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return result

def parse_brand_stat(data):
    """Return dict of BrandStat fields."""
    off, stat = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 4: stat['hits_total'] = v
            elif t == 5: stat['fans_count'] = v
            elif t == 6: stat['bought_count'] = v
            elif t == 7: stat['reserve_count'] = v
        elif wt == 2: _, off = read_ld(data, off)
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return stat

def parse_brand(data):
    """Parse BrandV5Brand: app(tag1), stat(tag11)."""
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            r, off = read_ld(data, off)
            if t == 1: result['app'] = parse_list_app_card(r)
            elif t == 11: result['stat'] = parse_brand_stat(r)
        elif wt == 0: _, off = read_varint(data, off)
        elif wt in (1,5): off += 8 if wt==1 else 4
    return result

def parse_mix_item(data):
    """Parse MixV5MixItem: all relevant fields."""
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 1: result['index'] = v
        elif wt == 2:
            r, off = read_ld(data, off)
            if t == 2:
                try: result['type'] = r.decode('utf-8')
                except: pass
            elif t == 6:  # BrandV5Brand
                result['brand'] = parse_brand(r)
            elif t == 9:  # ListAppCard (direct app)
                result['app'] = parse_list_app_card(r)
            elif t == 23:  # MixAppV5 (mix_app section)
                result['mix_app'] = parse_mix_app_v5(r)
        elif wt in (1,5): off += 8 if wt==1 else 4
    return result

def parse_mix_app_v5(data):
    """Parse MixAppV5: title(tag1), sub_title(tag2), list(tag7/repeated MixAppV5Item)."""
    off, result = 0, {'items': []}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            r, off = read_ld(data, off)
            if t == 1:
                try: result['title'] = r.decode('utf-8')
                except: pass
            elif t == 2:
                try: result['sub_title'] = r.decode('utf-8')
                except: pass
            elif t == 7:  # MixAppV5Item
                result['items'].append(parse_mix_app_v5_item(r))
        elif wt == 0: _, off = read_varint(data, off)
        elif wt in (1,5): off += 8 if wt==1 else 4
    return result

def parse_mix_app_v5_item(data):
    """Parse MixAppV5Item: type(tag1), app(tag3/ListAppCard)."""
    off, result = 0, {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            r, off = read_ld(data, off)
            if t == 1:
                try: result['type'] = r.decode('utf-8')
                except: pass
            elif t == 3:
                result['app'] = parse_list_app_card(r)
        elif wt == 0: _, off = read_varint(data, off)
        elif wt in (1,5): off += 8 if wt==1 else 4
    return result

def unwrap(data):
    """Strip outer wrapper + Any to get AggSearchV6Response bytes."""
    off = 0
    tw, off = read_varint(data, off)
    if (tw>>3)==1 and (tw&7)==0: _, off = read_varint(data, off)
    tw, off = read_varint(data, off)
    blob, off = read_ld(data, off)
    boff = 0
    tw, boff = read_varint(blob, boff); _, boff = read_ld(blob, boff)
    tw, boff = read_varint(blob, boff); value, _ = read_ld(blob, boff)
    return value

def parse_all(data):
    """Parse AggSearchV6Response: list(tag1/repeated MixV5AggItem)."""
    inner = unwrap(data)
    off, results = 0, []
    while off < len(inner):
        tw, off = read_varint(inner, off)
        wt, t = tw & 7, tw >> 3
        if wt == 2:
            agg_item, off = read_ld(inner, off)
            if t == 1:
                # Parse MixV5AggItem
                aoff = 0
                while aoff < len(agg_item):
                    tw2, aoff = read_varint(agg_item, aoff)
                    wt2, t2 = tw2 & 7, tw2 >> 3
                    if wt2 == 2:
                        r, aoff = read_ld(agg_item, aoff)
                        if t2 == 2:  # list of MixV5MixItem
                            results.append(parse_mix_item(r))
                    elif wt2 == 0: _, aoff = read_varint(agg_item, aoff)
                    elif wt2 in (1,5): aoff += 8 if wt2==1 else 4
        elif wt == 0: _, off = read_varint(inner, off)
        elif wt in (1,5): off += 8 if wt==1 else 4
    return results


if __name__ == '__main__':
    with open('post/agg-search_084559(1).txt', 'rb') as f:
        data = f.read()

    results = parse_all(data)

    # Print results with proper encoding
    sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("TapTap Search Suggest API Analysis")
    print("=" * 70)
    print("Endpoint: POST /search/v6/agg-search?X-ENC=pb")
    print("Request:  AggSearchV6Request { types=\"mix\", kw=\"心动小镇\", scene=\"suggest\", limit=10 }")
    print()

    for i, item in enumerate(results):
        item_type = item.get('type', 'unknown')
        print(f"--- Item {i+1} (type={item_type}) ---")

        # Brand result
        if 'brand' in item:
            brand = item['brand']
            app_info = brand.get('app', {})
            stat = brand.get('stat', {})
            print(f"  App:    {app_info.get('title', 'N/A')}")
            print(f"  Pkg:    {app_info.get('package_name', 'N/A')}")
            print(f"  ID:     {app_info.get('app_id', 'N/A')}")
            print(f"  Stats:  hits={stat.get('hits_total', 0):,}")
            print(f"          fans={stat.get('fans_count', 0):,}")
            print(f"          downloads={stat.get('bought_count', 0):,}")
            print(f"          reserve={stat.get('reserve_count', 0):,}")

        # Direct app result
        elif 'app' in item:
            app_info = item['app']
            print(f"  App:    {app_info.get('title', 'N/A')}")
            print(f"  Pkg:    {app_info.get('package_name', 'N/A')}")
            print(f"  ID:     {app_info.get('app_id', 'N/A')}")
            print(f"  Note:   No BrandStat for app-type results in suggest response")

        # MixAppV5 section (similar games)
        elif 'mix_app' in item:
            mix = item['mix_app']
            print(f"  Title:    {mix.get('title', 'N/A')}")
            print(f"  Subtitle: {mix.get('sub_title', 'N/A')}")
            for j, sub in enumerate(mix.get('items', [])):
                app = sub.get('app', {})
                if app:
                    print(f"  [{j+1}] {app.get('title', 'N/A')} ({app.get('package_name', 'N/A')})")

        # Other types
        else:
            print(f"  (no game data)")

        print()

    # API schema summary
    print("=" * 70)
    print("DATA SCHEMA (for game download counts in search suggest)")
    print("=" * 70)
    print("""
AggSearchV6Response
  └─ list (tag 1, repeated MixV5AggItem)
       └─ type (tag 1, string) = "mix"
       └─ list (tag 2, repeated MixV5MixItem)
            ├─ type (tag 2, string) = "brand" | "app" | "moment" | "mix_app" | ...
            ├─ brand (tag 6, BrandV5Brand)          ← branded games
            │    ├─ app (tag 1, ListAppCard)         ← game info
            │    │    ├─ id (tag 1, uint64)          ← brand/app ID
            │    │    ├─ identifier (tag 2, string)  ← package name
            │    │    └─ title (tag 5, string)       ← display name
            │    └─ stat (tag 11, BrandStat)         ★ DOWNLOAD STATS
            │         ├─ hits_total (tag 4, uint64)   ← total interactions/views
            │         ├─ fans_count (tag 5, uint64)   ← followers
            │         ├─ bought_count (tag 6, uint64) ← downloads/installs
            │         └─ reserve_count (tag 7, uint64)← pre-registrations
            └─ app (tag 9, ListAppCard)              ← non-branded apps (no stats)
""")
