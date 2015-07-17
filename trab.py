# coding=utf-8

from collections import namedtuple # nt()
RegSlot = namedtuple("Register_Slot", "regStart, regSize")
Rid = namedtuple('Register_ID', 'page, slot')
ntField = namedtuple("Field", "type max_size")

import struct
import mmap
import io

dCatalog = dict()

dCatalog["Scheme1"]["Table1"]["Attribute1"] = "int"
dCatalog["Scheme1"]["Table1"]["Attribute2"] = "varchar(64)"

PAGE_SIZE = 8192
QUATRO_GB = 4294967296


def my_open(file, offset=0) -> mmap.mmap:
	if isinstance(file, mmap.mmap):
	# received an actual mmap object that will be returned
		if not file.closed:
			file.flush(offset, PAGE_SIZE)
		return file # mmap
	elif isinstance(file, str):
	# path to the file
		file = open(file, mode='r+b', buffering=PAGE_SIZE)
	elif isinstance(file, io.FileIO):
	# file object that was already opened
		if file.closed:
			file = open(file.name, mode='r+b', buffering=PAGE_SIZE)
		else:
			file.flush()
	else: # invalid input
		return None

	return mmap.mmap(file.fileno(), PAGE_SIZE, offset=offset)


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
		super(Table, self).__init__()
		self.name = name
		self.archive = "tables/" + str(name)

		self.dAttributes = dAttributes # dicionário de características importantes para cada atributo
		#{ attr_name: nt(pos, type, max_size) , ...}

		self.nt_fields = nt_fields # vetor formatado de acordo com os atributos
		# [ ntField(type, max_size),  ... ]

		self.file = self.archive

		#self.regFmt = regFmt # string formatted for the struct module
		#self.regSize = int(struct.calcsize(regFmt)) # in bytes


	def insert(self, values:list):

		with open(self.archive, mode='r+b', buffering=PAGE_SIZE) as f:
			dir = DirectoryPage.load(f)
		# estimates row's size, and provides a formatted string for the struct module
			structFmt = "="
			size = 0
			fields_actual_size=[]
			for i, v in enumerate(values):
				if self.nt_fields[i]["type"] is "i":
					fields_actual_size.append(0)
					size += 4
					structFmt += "i"
				else:
					max = self.nt_fields[i]["max_size"]
					n = ( len(v) if len(v) < max  else max )
					size += n
					fields_actual_size.append(n)
					structFmt += "H" + str(n) + "s"

			reg = Register(size=size, fields=values, structFmt=structFmt, fields_actual_size=fields_actual_size)

			page = dir.insert(reg)
			page.insert(values, reg)



class DirectoryPage(object):
	dirFmt = '=IHI'
	dirSize = struct.calcsize(dirFmt)
	entryFmt = '=H'
	entrySize = struct.calcsize(entryFmt)

	def __init__(self, table:Table, baseAddr:int=0, numOfEntries:int=0, nextDir:int=0, entries:list=None):
		self.baseAddr = baseAddr
		self.numOfEntries = numOfEntries
		self.nextDir = nextDir
		self.entries = entries

		self.table = Table

	@staticmethod
	def load(table:Table, start:int=0) -> DirectoryPage:
		cls = DirectoryPage
		mm = my_open(table.file, start)

		base, n, next = struct.unpack_from(cls.dirFmt, mm, PAGE_SIZE-cls.dirSize)

		entries = []
		offset = 0
		for _ in range(n):
			entries.append(struct.unpack_from(cls.entryFmt, mm, offset)[0])
			offset += cls.entrySize

		return cls(base, n, next, entries, file)

	#todo arrumar a criação de uma RegisterPage
	@staticmethod
	def create(table:Table, baseAddr:int) -> int:
		cls = DirectoryPage

		pageNumber = RegisterPage.create()
		pageSize = RegisterPage.emptySize
		newDir = cls(table, baseAddr, 1, 0, [pageSize])
		newDir.save()
		return newDir.baseAddr

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
		registerSize = Reg.size
	# tries to find a page with empty space
		for i, e in enumerate(self.entries):
			if e >= registerSize:
				pageNumber = self.baseAddr * i
				page = RegisterPage.load(self.table.file, start=pageNumber)
				if page.insert(Reg):
					return page
				#return self.baseAddr * i
	#
		if not self.is_full():
			# DirectoryPage has room for another page entry
			return self.new_entry(Reg)

	# no page with empty space in this directory
		if not self.nextDir:
			# directory's pages ended; should create a new one
			b = PAGE_SIZE*self.numOfEntries + self.baseAddr
			self.nextDir = cls.create(file=self.file, baseAddr=b)
		# going to check if there is empty space in the next directory page
		dir = DirectoryPage.load(self.file, self.nextDir)
		return dir.insert(Reg)

	def is_full(self) -> bool:
		cls = DirectoryPage

		usedSpace = (self.numOfEntries * cls.entrySize) + cls.dirSize
		freeSpace = PAGE_SIZE - usedSpace
		return (False if freeSpace > cls.entrySize  else True)

	def new_entry(self, Reg:Register):
		cls = DirectoryPage

		self.entries.append([PAGE_SIZE])

		regPage = RegisterPage(baseAddr=self.baseAddr)



class RegisterPage(object):
	metaFmt = "=HH" # (startOfFreeSpace, numOfSlots)
	metaSize = struct.calcsize(metaFmt) # size of header fields in this page
	slotFmt = "=Ih"
	slotSize = struct.calcsize(slotFmt)

	emptySize = metaSize + slotSize

	def __init__(self, table:Table, numOfSlots:int=0, slots:list=None, baseAddr:int=0, startOfFreeSpace:int=0, registers:list=None):
		self.startOfFreeSpace = startOfFreeSpace
		self.numOfSlots = numOfSlots
		self.slots = slots

		self.table = table
		self.baseAddr = baseAddr
		self.registers = registers


	@staticmethod
	def load(table:Table, baseAddr:int=0) -> __init__:
		cls = RegisterPage
		mm = my_open(table.file, baseAddr)
	# loads meta information
		free, numSlots = struct.unpack_from(cls.metaFmt, mm, PAGE_SIZE-cls.metaSize)
	# loads slots
		slots = []
		offset = 0
		for _ in range(numSlots):
			a, b = struct.unpack_from(cls.slotFmt, mm, offset)
			slots.append(RegSlot(a, b))
			offset += cls.slotSize
	# for each slot in the page, creates a register
		registers = []
		for i_slot, slot in enumerate(slots):
			rid = Rid(baseAddr, i_slot)
			reg = Register.load(table.file, rid, slot)
			Register.load
			registers.append(reg)
		# creates a RegisterPage and returns that object
		return RegisterPage(table, numOfSlots=numSlots, slots=slots, baseAddr=baseAddr, startOfFreeSpace=freeSpace, registers=registers)
	#END load()

	@staticmethod
	def create(file:io.IOBase, baseAddr):
		page = RegisterPage(file=file, baseAddr=baseAddr)
		page.save()


		return 1

#todo talvez haverá a necessidade de salvar também a basePage.
	def save(self):
		cls = RegisterPage
		mm = my_open(self.table.file, self.baseAddr)

		struct.pack_into(cls.metaFmt, mm, 0, self.startOfFreeSpace, self.numOfSlots)

		for i, slot in enumerate(self.slots):
		# this first part stores slots
			offset = (i * cls.slotSize) + cls.metaSize
			struct.pack_into(cls.slotFmt, mm, offset, *slot)
		# this part stores registers
			if slot.regSize < 0:
				# there is no register associated with that slot
				continue
			reg = self.registers[i]

	#END save()


	def insert(self, Reg:Register):
		cls = RegisterPage
	# checks if there's an unused slot that can hold the register
		for i, s in enumerate(self.slots):
			if s.regSize < 0 and s.regSize >= Reg.size:
				# makes regSize positive to show space usage
				s.regSize *= -1
				# stores in which page and slot the Register can be found
				Reg.rid = Rid(self.baseAddr, i)
				return True
	# checks if there's enough space in this page to store the new register and slot
		spaceRequired = Reg.size + cls.slotSize
		dirSpace = cls.metaSize + (self.numOfSlots * cls.slotSize)
		spaceGranted = PAGE_SIZE - self.startOfFreeSpace - dirSpace
		if spaceRequired > spaceGranted:
			# can't insert the register in this page
			return False
	# creates a new slot and stores the register
		newSlot = RegSlot(self.startOfFreeSpace, Reg.size)
		self.slots.append(newSlot)
		self.numOfSlots += 1
		self.startOfFreeSpace += Reg.size
		# stores in which page and slot the Register can be found
		Reg.rid = Rid(self.baseAddr, self.numOfSlots-1)
		return True
	#END insert()


class Register(object):
	"""docstring for Register"""
	
	def __init__(self, table:Table, size:int=0, fields:list=[], fields_actual_size:list=[], structFmt:str="",  rid:Rid=Rid(0,0)):
		super(Register, self).__init__()
		self.rid = rid
		self.size = size
		
		self.fields = fields
		
		self.fields_actual_size = fields_actual_size
		self.structFmt = structFmt
		self.table = table
		#self.space =

	@staticmethod
	def load(table:Table, rid:Rid, slot:RegSlot) -> __init__:
		if slot.regSize < 0:
			# there is no register associated with that slot
			return None
		mm = my_open(table.file, rid.page)
	#for each field in the Register, updates the following variables
		finalFmt = "=" # used with struct module
		finalSize = 0 	
		fields, fields_actual_size = [], []
		offset = slot.regStart
		for field in table.nt_fields:
			if field.type == 's': # string type
			# needs to load fields size before loading the actual fields value
				size = struct.unpack_from('H', mm, offset)
				fields_actual_size.append(size)
				offset += size
				fmt = str(size) + 's'
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
		reg = Register(size=finalSize, fields=fields, fields_actual_size=fields_actual_size, structFmt=finalFmt, rid=rid)
		return reg

#todo olhar a parte do slot nesse save, talvez precisará receber ele como parâmetro
	def save(self):
		""" since registers can have strings of mutable size, they need to store how much space is allocated for each string. Thus, we will get fields and fields size into "values"."""
		mm = my_open(self.table.file, self.rid.page)
		values = []
		for f in self.fields:
			try: int(f)
			except: values.append(len(f))
			values.append(f)
		struct.pack_into(self.structFmt, mm, slot.regStart, *values)
