"""Bounded MVP-style Wasm metadata reader; never compile or execute a module."""
import hashlib


class UnsupportedFeature(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data, self.offset = data, 0

    def take(self, size):
        if size < 0 or self.offset + size > len(self.data):
            raise ValueError('Truncated Wasm metadata')
        result = self.data[self.offset:self.offset + size]
        self.offset += size
        return result

    def byte(self):
        return self.take(1)[0]

    def u32(self):
        value = 0
        for index in range(5):
            byte = self.byte()
            if index == 4 and byte & 0xf0:
                raise ValueError('u32 LEB overflow')
            value |= (byte & 127) << (7 * index)
            if not byte & 128:
                return value
        raise ValueError('u32 LEB overflow')

    def count(self):
        value = self.u32()
        if value > 100000:
            raise UnsupportedFeature('Metadata vector exceeds inspection limit')
        return value

    def name(self):
        return self.take(self.u32()).decode('utf-8')

    def limits(self):
        flags = self.u32()
        if flags not in (0, 1, 2, 3):
            raise UnsupportedFeature('Non-MVP limits/memory64 not supported by this reader')
        return {'flags': flags, 'min': self.u32(), 'max': self.u32() if flags & 1 else None}


def inspect(data):
    reader = Reader(data)
    if reader.take(8) != b'\x00asm\x01\x00\x00\x00':
        raise ValueError('Not a Wasm version 1 binary')
    sections = {}
    while reader.offset < len(data):
        kind, size = reader.byte(), reader.u32()
        contents = reader.take(size)
        if kind:
            if kind in sections:
                raise ValueError('Duplicate non-custom section')
            sections[kind] = contents
    types, functions, imports, exports, memories = [], [], [], [], []
    if 1 in sections:
        r = Reader(sections[1])
        for _ in range(r.count()):
            if r.byte() != 0x60:
                raise UnsupportedFeature('Non-function/recursive type not supported')
            params = [hex(r.byte()) for _ in range(r.count())]
            results = [hex(r.byte()) for _ in range(r.count())]
            types.append({'params': params, 'results': results})
    if 2 in sections:
        r = Reader(sections[2])
        for _ in range(r.count()):
            item = {'module': r.name(), 'name': r.name(), 'kind': r.byte()}
            kind = item['kind']
            if kind == 0:
                index = r.u32()
                item['type'] = types[index]
                functions.append(index)
            elif kind == 1:
                item.update(element_type=hex(r.byte()), limits=r.limits())
            elif kind == 2:
                item['limits'] = r.limits()
                memories.append(item['limits'])
            elif kind == 3:
                item.update(value_type=hex(r.byte()), mutable=r.byte())
            elif kind == 4:
                item.update(attribute=r.u32(), type_index=r.u32())
            else:
                raise UnsupportedFeature('Unknown import kind')
            imports.append(item)
    if 3 in sections:
        r = Reader(sections[3])
        functions.extend(r.u32() for _ in range(r.count()))
    if 5 in sections:
        r = Reader(sections[5])
        memories.extend(r.limits() for _ in range(r.count()))
    if 7 in sections:
        r = Reader(sections[7])
        for _ in range(r.count()):
            item = {'name': r.name(), 'kind': r.byte(), 'index': r.u32()}
            if item['kind'] == 0:
                item['type'] = types[functions[item['index']]]
            exports.append(item)
    start = Reader(sections[8]).u32() if 8 in sections else None
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'imports': imports,
            'exports': exports, 'start': start, 'memories': memories}
