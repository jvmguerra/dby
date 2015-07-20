# coding=utf-8
class Table: pass
class DirectoryPage: pass
class RegisterPage: pass
class Register: pass

from collections import namedtuple # nt()
RegSlot = namedtuple("Register_Slot", "regStart, regSize")
Rid = namedtuple('Register_ID', 'page, slot')
ntField = namedtuple("Field", "type max_size")

import struct
import mmap
import io

dCatalog = dict()

# dCatalog["Scheme1"]["Table1"]["Attribute1"] = "int"
# dCatalog["Scheme1"]["Table1"]["Attribute2"] = "varchar(64)"

PAGE_SIZE = 8192
QUATRO_GB = 4294967296


def my_open(file, offset=0, size=PAGE_SIZE) -> mmap.mmap:
	if isinstance(file, mmap.mmap):
	# received an actual mmap object that will be returned
		if not file.closed:
			file.flush(offset, size)
		return file # mmap
	elif isinstance(file, str):
	# path to the file
		file = open(file, mode='r+b', buffering=size)
	elif isinstance(file, io.FileIO):
	# file object that was already opened
		if file.closed:
			file = open(file.name, mode='r+b', buffering=size)
		else:
			file.flush()
	else: # invalid input
		return None

	return mmap.mmap(file.fileno(), size, offset=offset)


def create_table(table:str, dAttributes:dict, nt_fields:list):
	dCatalog[table] = Table(table, dAttributes, nt_fields)
	open("tables\\"+table, mode='wb', buffering=0)
	print(dCatalog[table].file)

def insert(table:str, values:list):
	dCatalog[table].insert(values)


class Catalog(object):
	"""docstring for Catalog"""
	def __init__(self):
		super(Catalog, self).__init__()
		self.dSchemes = {}

class Scheme(object):
	"""docstring for Scheme"""
	def __init__(self):
		super(Scheme, self).__init__()
		self.name = ""
		self.dTables = {}
		self.directory = ""

class Table(object):
	"""docstring for Table"""
	def __init__(self, name:str, dAttributes:dict, nt_fields:list):
		self.name = name
		self.archive = "tables\\" + str(name)

		self.dAttributes = dAttributes # dicionário de características importantes para cada atributo
		#{ attr_name: nt(pos, type, max_size) , ...}

		self.nt_fields = nt_fields # vetor formatado de acordo com os atributos
		# [ ntField(type, max_size),  ... ]

		self.file = self.archive

		#self.regFmt = regFmt # string formatted for the struct module
		#self.regSize = int(struct.calcsize(regFmt)) # in bytes


	def insert(self, values:list):
	# estimates row's size, and provides a formatted string for the struct module
		structFmt = "="
		size = 0
		fields_actual_size=[]
		for i, v in enumerate(values):
			if self.nt_fields[i].type is "i":
				fields_actual_size.append(0)
				size += 4
				structFmt += "i"
			else:
				max = self.nt_fields[i].max_size
				n = ( len(v) if len(v) < max  else max )
				size += n
				fields_actual_size.append(n)
				structFmt += "H" + str(n) + 'c'
		# makes a Register with above variables
		reg = Register(self, size=size, fields=values, structFmt=structFmt, fields_actual_size=fields_actual_size)
		# loads the first DirectoryPage of this Table
		dir = DirectoryPage.load(self)
		dir.insert(reg)



class DirectoryPage(object):
	dirFmt = '=IHI'
	dirSize = struct.calcsize(dirFmt)
	entryFmt = '=H'
	entrySize = struct.calcsize(entryFmt)

	def __init__(self, table:Table, baseAddr:int=0, numOfEntries:int=0, nextDir:int=0, entries:list=None):
		self.baseAddr = baseAddr
		self.numOfEntries = numOfEntries
		self.nextDir = nextDir
		if not entries:
			self.entries = []

		self.table = table

	@staticmethod
	def load(table:Table, base:int=0) -> __init__:
		cls = DirectoryPage
		mm = my_open(table.file, base)

		base, n, next = struct.unpack_from(cls.dirFmt, mm, PAGE_SIZE-cls.dirSize)

		entries = []
		offset = 0
		for _ in range(n):
			entries.append(struct.unpack_from(cls.entryFmt, mm, offset)[0])
			offset += cls.entrySize

		return cls(table, base, n, next, entries)

	def save(self):
		cls = DirectoryPage
		mm = my_open(self.table.file, self.baseAddr)

		struct.pack_into(cls.dirFmt, mm, PAGE_SIZE-cls.dirSize, self.baseAddr, self.numOfEntries, self.nextDir)

		offset = 0
		for i in range(self.numOfEntries):
			struct.pack_into(cls.entryFmt, mm, offset, self.entries[i])
			offset += cls.entrySize

	def insert(self, Reg:Register) -> int:
		cls = DirectoryPage

		if not self.entries:
			# directory page is totally empty
			return self.new_entry(Reg)
	# tries to find a page with empty space
		for i, e in enumerate(self.entries):
			if e >= Reg.size:
				pageNumber = self.baseAddr * i
				page = RegisterPage.load(self.table, baseAddr=pageNumber)
				if page.insert(Reg):
					self.entries[i] -= Reg.size
					self.save()
					return page
				#return self.baseAddr * i
		if not self.is_full():
			# DirectoryPage has room for another page entry
			return self.new_entry(Reg)
	# no page with empty space in this full filled directory
		if not self.nextDir:
			# directory's pages ended; should create a new one
			base = (PAGE_SIZE * self.numOfEntries) + self.baseAddr
			self.nextDir = base
			self.save()
			newDir = RegisterPage(self.table, base)
			return newDir.insert(Reg)
	# going to check if there is empty space in the next directory page
		dir = DirectoryPage.load(self.table, self.nextDir)
		return dir.insert(Reg)

	def is_full(self) -> bool:
		cls = DirectoryPage

		usedSpace = (self.numOfEntries * cls.entrySize) + cls.dirSize
		freeSpace = PAGE_SIZE - usedSpace
		return (False if freeSpace > cls.entrySize  else True)

	def new_entry(self, Reg:Register) -> int:
		"""
		Creates a new entry and inserts the Register in the corresponding RegisterPage.
		:param Reg:
		:return:
		"""
		self.entries.append(PAGE_SIZE - Reg.size)
		self.numOfEntries += 1
		base = len(self.entries) * self.baseAddr
		regPage = RegisterPage(self.table, base)
		regPage.insert(Reg)
		self.save()
		return base



class RegisterPage(object):
	metaFmt = "=HH" # (startOfFreeSpace, numOfSlots)
	metaSize = struct.calcsize(metaFmt) # size of header fields in this page
	slotFmt = "=Ih"
	slotSize = struct.calcsize(slotFmt)

	emptySize = metaSize + slotSize

	def __init__(self, table, baseAddr:int, numOfSlots:int=0, slots:list=None, startOfFreeSpace:int=0, registers:list=None):
		self.startOfFreeSpace = startOfFreeSpace
		self.numOfSlots = numOfSlots
		self.slots = (slots if slots  else [])
		self.table = table
		self.baseAddr = baseAddr
		self.registers = (registers if registers  else [])


	@staticmethod
	def load(table:Table, baseAddr:int) -> __init__:
		cls = RegisterPage
		mm = my_open(table.file, baseAddr)
	# loads meta information
		offset = PAGE_SIZE - cls.metaSize
		free, numSlots = struct.unpack_from(cls.metaFmt, mm, offset)
	# loads slots
		slots = []
		for _ in range(numSlots):
			offset -= cls.slotSize
			a, b = struct.unpack_from(cls.slotFmt, mm, offset)
			slots.append(RegSlot(a, b))
	# for each slot in the page, creates a register
		registers = []
		for i_slot, slot in enumerate(slots):
			if slot.regSize < 0:
				# there is no register associated with that slot
				registers.append(None)
				continue
			rid = Rid(baseAddr, i_slot)
			reg = Register.load(table, rid, mm[slot.regStart:slot.regSize])
			registers.append(reg)
		# creates a RegisterPage and returns that object
		return RegisterPage(table, baseAddr, numOfSlots=numSlots, slots=slots, startOfFreeSpace=free, registers=registers)
	#END load()


#todo talvez haverá a necessidade de salvar também a basePage.
	# aparentemente não precisa pq nas principais operações já tem um baseAddr
	def save(self):
		cls = RegisterPage
		mm = my_open(self.table.file, self.baseAddr)

		offset = PAGE_SIZE - cls.metaSize
		struct.pack_into(cls.metaFmt, mm, offset, self.startOfFreeSpace, self.numOfSlots)

		for i, slot in enumerate(self.slots):
		# this first part stores slots
			offset -= cls.slotSize
			struct.pack_into(cls.slotFmt, mm, offset, *slot)
		# this part stores registers
			if slot.regSize < 0:
				# there is no register associated with that slot
				continue
			reg = self.registers[i]
			mm[slot.regStart:slot.regSize] = reg.save()
	#END save()


	def insert(self, Reg:Register) -> bool:
		if not self.slots:
			# this page its completely empty
			self.new_slot(Reg)
			self.save()
			return True
	# checks if there's an unused slot that can hold the register
		for i, s in enumerate(self.slots):
			if s.regSize < 0 and s.regSize >= Reg.size:
				# makes regSize positive to show space usage
				s.regSize *= -1
				# stores in which page and slot the Register can be found
				Reg.rid = Rid(self.baseAddr, i)
				self.registers[i] = Reg
				self.save()
				return True
	# checks if there's enough space in this page to store the new register and slot
		if not self.has_space(Reg.size):
			return False
	# creates a new slot and stores the register
		self.new_slot(Reg)
		self.save()
		return True
	#END insert()

	def has_space(self, size:int) -> bool:
		cls = RegisterPage
		spaceRequired = size + cls.slotSize
		dirSpace = cls.metaSize + (self.numOfSlots * cls.slotSize)
		spaceGranted = PAGE_SIZE - self.startOfFreeSpace - dirSpace
		if spaceRequired > spaceGranted:
			# can't insert the register in this page
			return False
		else: # has space
			return True

	def new_slot(self, Reg:Register):
		# stores in which page and slot the Register can be found
		Reg.rid = Rid(self.baseAddr, self.numOfSlots-1)
		newSlot = RegSlot(self.startOfFreeSpace, Reg.size)
		self.slots.append(newSlot)
		self.registers.append(Reg)
		self.numOfSlots += 1
		self.startOfFreeSpace += Reg.size



class Register(object):
	"""docstring for Register"""

	def __init__(self, table:Table, size:int=0, fields:list=None, fields_actual_size:list=None, structFmt:str="",  rid:Rid=Rid(0,0)):
		self.rid = rid
		self.size = size
		self.fields = (fields if fields  else [])
		self.fields_actual_size = (fields_actual_size if fields_actual_size  else [])
		self.structFmt = structFmt
		self.table = table
		#self.space =

	@staticmethod
	def load(table:Table, rid:Rid, mm:mmap.mmap) -> __init__:
	# for each field in the Register, updates the following variables
		finalFmt = "=" # used with struct module
		finalSize = 0
		fields = []
		fields_actual_size = []
		offset = 0
		for field in table.nt_fields:
			if field.type == 'c': # string type
			# needs to load fields size before loading the actual fields value
				size = struct.unpack_from('H', mm, offset)
				fields_actual_size.append(size)
				offset += size
				fmt = str(size) + 'c'
				finalFmt += 'H'
			else: # integer type
				fmt = 'i'
				size= 4
				fields_actual_size.append(0)
			finalFmt += fmt
			finalSize += size
			fields.append(struct.unpack_from(fmt, mm, offset))
			offset += field.size
		# creates a Register and returns it
		return Register(table, size=finalSize, fields=fields, fields_actual_size=fields_actual_size, structFmt=finalFmt, rid=rid)

#todo ver como transformar uma string para bytes, pq o modulo struct só aceita bytes
	def save(self) -> bytes:
		""" since registers can have strings of mutable size, they need to store how much space is allocated for each string. Thus, we will get fields and fields size into "values"."""
		print(self.rid)
		values = []
		for f in self.fields:
			try: int(f)
			except: values.append(len(f))
			values.append(f)
		print(values)
		print(self.structFmt)
		return struct.pack(self.structFmt, *values)

