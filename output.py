import struct
import io
import mmap



f = open("teste", mode='r+b', buffering=4096)
#x = bytearray(f.read())

x= mmap.mmap(f.fileno(), 0, offset=0)


print(len(x))
a= 18
b = 42
c = -2

struct.pack_into("=IHi", x, 0, a, b, c)

