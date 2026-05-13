"""Debug: enumerate all items in the MixV5AggItem list."""
import sys

def read_varint(data, offset):
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80):
            break
        shift += 7
    return value, offset

def read_ld(data, offset):
    length, offset = read_varint(data, offset)
    return data[offset:offset + length], offset + length

def parse_list_app_card(data):
    """Return (title, pkg, app_id) from ListAppCard."""
    off = 0
    title = b''
    pkg = b''
    app_id = 0
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 1: app_id = v
        elif wt == 2:
            r, off = read_ld(data, off)
            if t == 2: pkg = r
            elif t == 5: title = r
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return title, pkg, app_id

def parse_brand_stat(data):
    """Return dict of BrandStat fields."""
    off = 0
    stat = {}
    while off < len(data):
        tw, off = read_varint(data, off)
        wt, t = tw & 7, tw >> 3
        if wt == 0:
            v, off = read_varint(data, off)
            if t == 4: stat['hits_total'] = v
            elif t == 5: stat['fans_count'] = v
            elif t == 6: stat['bought_count'] = v
            elif t == 7: stat['reserve_count'] = v
        elif wt == 2:
            _, off = read_ld(data, off)
        elif wt == 1: off += 8
        elif wt == 5: off += 4
    return stat

with open('post/agg-search_084559(1).txt', 'rb') as f:
    data = f.read()

# Unwrap to AggSearchV6Response
off = 0
tag_wire, off = read_varint(data, off)
if (tag_wire >> 3) == 1 and (tag_wire & 7) == 0:
    _, off = read_varint(data, off)
tag_wire, off = read_varint(data, off)
blob, off = read_ld(data, off)
boff = 0
tag_wire, boff = read_varint(blob, boff)
_, boff = read_ld(blob, boff)
tag_wire, boff = read_varint(blob, boff)
inner, _ = read_ld(blob, boff)

# Parse AggSearchV6Response -> MixV5AggItem
off = 0
tag_wire, off = read_varint(inner, off)
agg_item, off = read_ld(inner, off)
print(f'AggItem size: {len(agg_item)} bytes')
print()

# Parse MixV5AggItem: enumerate all tag 2 fields
aoff = 0
item_num = 0
while aoff < len(agg_item):
    tag_wire, aoff = read_varint(agg_item, aoff)
    wire_type = tag_wire & 7
    tag = tag_wire >> 3
    if wire_type == 2:
        raw, aoff = read_ld(agg_item, aoff)
        if tag == 1:
            try:
                print(f'AggItem.type = {raw.decode("utf-8")}')
            except:
                print(f'AggItem.type = {raw!r}')
        elif tag == 2:
            item_num += 1
            # Walk MixV5MixItem fields
            mioff = 0
            item_type = b''
            title = b''
            pkg = b''
            app_id = 0
            stat = {}
            while mioff < len(raw):
                tw, mioff = read_varint(raw, mioff)
                wt = tw & 7
                t = tw >> 3
                if wt == 0:
                    v, mioff = read_varint(raw, mioff)
                    if t == 1: app_id = v
                elif wt == 2:
                    r, mioff = read_ld(raw, mioff)
                    if t == 2:  # type
                        item_type = r
                    elif t == 6:  # BrandV5Brand
                        broff = 0
                        while broff < len(r):
                            btw, broff = read_varint(r, broff)
                            bwt, bt = btw & 7, btw >> 3
                            if bwt == 2:
                                br, broff = read_ld(r, broff)
                                if bt == 1:  # ListAppCard
                                    title, pkg, app_id = parse_list_app_card(br)
                                elif bt == 11:  # BrandStat
                                    stat = parse_brand_stat(br)
                            elif bwt == 0:
                                _, broff = read_varint(r, broff)
                            elif bwt == 1: broff += 8
                            elif bwt == 5: broff += 4
                    elif t == 9:  # ListAppCard (direct app)
                        title, pkg, _ = parse_list_app_card(r)
                elif wt == 1: mioff += 8
                elif wt == 5: mioff += 4

            print(f'--- Item {item_num} ---')
            try:
                print(f'  type:  {item_type.decode("utf-8")}')
            except:
                print(f'  type:  {item_type!r}')
            try:
                print(f'  title: {title.decode("utf-8")}')
            except:
                print(f'  title: {title!r}')
            try:
                print(f'  pkg:   {pkg.decode("utf-8")}')
            except:
                print(f'  pkg:   {pkg!r}')
            print(f'  id:    {app_id}')
            if stat:
                for k, v in stat.items():
                    print(f'  {k}: {v:,}')
            print()
    elif wire_type == 0:
        _, aoff = read_varint(agg_item, aoff)
    elif wire_type in (1, 5):
        aoff += 8 if wire_type == 1 else 4
