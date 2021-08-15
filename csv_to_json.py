import json
import re
import os.path
import itertools
from functools import partialmethod

from unidecode import unidecode

# This is the newest version, use this

ENGLISH = "english"
DINE = "dine"
AUDIO_PATH = "/audio/"

# TODO add line numbers
CSV_DIVIDER = "\t"
defaults = ("English word", "Diné word", "No definition provided",
            "No definition provided", None, None)

eng_audio = os.listdir(os.curdir + AUDIO_PATH + ENGLISH)
dine_audio = os.listdir(os.curdir + AUDIO_PATH + DINE)

ref_pattern = re.compile(r"@(\d)$")
normalization_table = str.maketrans(" ", "-", "'(),.")


# surprised there isn't something that does this already
# def default(*args):
# 	for arg in args:
# 		if arg:
# 			return arg
# 	return ""


def default_plus(val, default):
	if val:
		return val.replace("\"\"", "\"")  # TODO more tidying.
	# in particular, strip leading and trailing double-quote
	elif default:
		return default
	return ""


def first(iterable, func):
	try:
		return next(filter(func, iterable))
	except StopIteration:
		return False


def normalize(accented_string):
	return unidecode(accented_string).translate(normalization_table).lower()


def get_audio(lang, word, filename, directory):
	if not filename:
		filename = normalize(word)
	audio_path = filename + "-" + lang + ".m4a"
	if audio_path in directory:
		return AUDIO_PATH + audio_path
	return ""


def get_field(e, field):
	try:
		return getattr(e, field)
	except AttributeError:
		return e[field]


def get_reference(text):
	return re.match(ref_pattern, text).group(1)


def keyfunc_eng(r):
	return normalize(r.english)


def keyfunc_dine(r):
	return normalize(r.navajo)


class Row:
	def __init__(self, row):
		(self.english,
		 self.variant_eng,
		 self.variant_navajo,
		 self.navajo,
		 self.def_eng,
		 self.def_navajo,
		 self.literal,
		 self.comment,
		 self.see_also_eng,
		 self.see_also_navajo,
		 self.sentence_eng,
		 self.sentence_navajo,
		 self.phonetic_eng,
		 self.phonetic_navajo,
		 self.audio_english,
		 self.audio_navajo
		 ) = [x.strip() for x in row]
		self.normalized_eng = normalize(self.english)
		self.normalized_navajo = normalize(self.navajo)

class RawRows:
	def __init__(self):
		self.eng = {}
		self.dine = {}


raw_rows = RawRows()


class SeeAlso:
	def __init__(self, word):
		self.word = word
		self.normalized = normalize(word)
	
	@staticmethod
	def get_see_also(attr: str):
		def get_see_also_row(row: Row):
			return [SeeAlso(sa).dump() for sa in getattr(row, attr).split(", ") if sa]
		
		return get_see_also_row
	
	def dump(self):
		return self.__dict__

class SeeAlsos:
	def __init__(self):
		self.entries = {}
	
	def add_row(self, attr, row):
		see_also = getattr(row, attr)
		ref_match = ref_pattern.match(see_also)
		if ref_match:
			# it's an @ reference
			see_also = getattr(raw_rows.eng[(row.english, ref_match.group(1))], attr)
		
		for word in see_also.split(", "):
			if word:
				self.entries[normalize(word)] = word
		
	def add(self, attr):
		return partialmethod(self.add_row, attr)
	
	def dump(self):
		return [{"word": word, "normalized": normalized} for (normalized, word) in self.entries.items()]
	
	
class Dictionary:
	def __init__(self, lines):
		self.english = {}
		self.navajo = {}
		
		unsorted_rows = [Row(line.strip("\n").split(CSV_DIVIDER)) for line in lines]
		# sort to ensure that we don't reference variants we haven't seen yet
		rows = sorted(unsorted_rows, key=lambda r: normalize(r.english) + r.variant_eng)
		
		# I think doing something like this and establishing a lookup would make things
		# much easier when trying to get variants
		raw_rows.eng = {(row.english, row.variant_eng): row for row in
		                sorted(rows, key=keyfunc_eng)}
		raw_rows.dine = {(row.navajo, row.variant_navajo): row for row in
		                 sorted(rows, key=keyfunc_dine)}
		
		eng_rows = itertools.groupby(sorted(rows, key=keyfunc_eng), keyfunc_eng)
		navajo_rows = itertools.groupby(sorted(rows, key=keyfunc_dine), keyfunc_dine)
		
		for (eng_key, word_rows) in eng_rows:
			entry = EngToDine(eng_key)
			
			for row in word_rows:
				entry.add(row)
			self.english[eng_key] = entry
		
		for (navajo_key, word_rows) in navajo_rows:
			entry = DineToEng(navajo_key)
			
			for row in word_rows:
				entry.add(row)
			self.navajo[navajo_key] = entry
	
	def dump(self, out):
		english = {k: e.dump() for (k, e) in self.english.items()}
		navajo = {k: e.dump() for (k, e) in self.navajo.items()}
		json.dump({"entries": {"english": english, "navajo": navajo}},
		          out, indent=2, ensure_ascii=False)


# TODO EngToDine and DineToEng can still be merged I think
class EngToDine:
	keys = {
		"word": "navajo",
		"variant": "variant_eng",
		"literal": None,  # None means "just use the key". e.g. here look for "literal"
		"comment": None,
		"see_also": SeeAlso.get_see_also("see_also_navajo")
	}
	
	def __init__(self, word):
		self.word = ""
		self.normalized = word
		self.definition = ""
		self.sentence = ""
		self.phonetic = ""
		self.audio = ""
		self.see_also = []
		self.short_translations = []
		self.translations = Translations("def_navajo", self.keys)
	
	def add(self, row):
		self.word = row.english
		if not ref_pattern.match(row.def_eng):
			self.definition = row.def_eng
		if not ref_pattern.match(row.sentence_eng):
			self.sentence = row.sentence_eng
		if not ref_pattern.match(row.phonetic_eng):
			self.phonetic = row.phonetic_eng
		if not ref_pattern.match(row.see_also_eng):
			self.see_also = SeeAlso.get_see_also("see_also_eng")(row)
		
		self.audio = get_audio(ENGLISH, row.english, row.audio_english, eng_audio)
		
		self.short_translations.append(row.navajo)
		self.translations.add(row)
	
	def dump(self):
		out = {k: v for (k, v) in self.__dict__.items() if v}
		out["translations"] = self.translations.dump()
		return out


class Settable:
	def __init__(self):
		self.data = {}
	
	def set(self, row, source, destination):
		if not source:
			source = destination
		
		try:
			# is it callable?
			value = source(row)
		except TypeError:
			# it is not callable
			value = getattr(row, source)
		
		
		try:
			ref_match = ref_pattern.match(value)
			if ref_match:
				# it's an @ reference
				value = getattr(raw_rows.eng[(row.english, ref_match.group(1))], source)
		except TypeError:
			# it's not a string, actually
			pass
		
		if value:
			self.data[destination] = value


class DineToEng(Settable):
	keys = {
		"word": "navajo",
		"normalized": "normalized_navajo",
		"definition": "def_navajo",
		"literal": "literal",
		"sentence": "sentence_navajo",
		"phonetic": "phonetic_navajo",
		# "see_also": SeeAlso.get_see_also("see_also_navajo"),
		"audio": lambda row: get_audio(DINE, row.english, row.audio_navajo, dine_audio)
	}
	keys2 = {
		"definition": "def_eng",
		"see_also": SeeAlso.get_see_also("see_also_eng")
	}
	keys3 = {
		"word": "english",
		"normalized": "normalized_eng",
		"variant": "variant_navajo",
		"comment": None
	}
	
	def __init__(self, word):
		super().__init__()
		self.word = word
		# self.see_also = []
		self.see_also = SeeAlsos()
		self.short_translations = []
		# self.translations = Translations2("def_eng", "see_also_eng", self.keys3)
		self.translations = {}
	
	def add(self, row):
		for (key, source) in self.keys.items():
			self.set(row, source, key)
		
		self.short_translations.append(row.english)
		# self.translations.add(row)
		self.add_translation(row)
		self.see_also.add("see_also_navajo")
	
	def add_translation(self, row):
		definition = getattr(row, "def_eng")
		translation = self.translations.setdefault(definition, Translation(self.keys, row))
		translation.add(row, self.keys3)
		translation.see_also.add_row("see_also_eng", row)
	
	def dump(self):
		out = {k: v for (k, v) in self.data.items() if v}
		out["short_translations"] = self.short_translations
		# out["translations"] = self.translations.dump()
		out["translations"] = [t.dump() for t in self.translations.values()]
		return out


# class Translations2:
# 	def __init__(self, def_key, see_also_key, sub_keys):
# 		self.def_key = def_key
# 		self.see_also_key = see_also_key
# 		self.keys = {
# 			"definition": def_key
# 		}
# 		self.sub_keys = sub_keys
# 		self.entries = {}
#
# 	def add(self, row):
# 		definition = getattr(row, self.def_key)
#
# 		translation = self.entries.setdefault(definition, Translation(self.keys, row))
#
# 		# # you may end up using this snippet for that, instead of setdefault
# 		# if definition not in self.entries:
# 		# 	self.entries[definition] = Translation(self.keys, row)
# 		# translation = self.entries[definition]
#
# 		translation.add(row, self.sub_keys)
# 		translation.see_also.add_row(self.see_also_key, row)
#
#
# 	def dump(self):
# 		return [e.dump() for e in self.entries.values()]


class Translation(Settable):
	def __init__(self, keys, row):
		super().__init__()
		self.see_also = SeeAlsos()
		self.entries = []
		for (destination, source) in keys.items():
			self.set(row, source, destination)
	
	def add(self, row, sub_keys):
		self.entries.append(TranslationEntry(sub_keys, row))
	
	def dump(self):
		out = {k: v for (k, v) in self.data.items() if v}
		out["see_also"] = self.see_also.dump()
		out["entries"] = [e.dump() for e in self.entries]
		return out
	
	
class TranslationEntry(Settable):
	def __init__(self, keys, row):
		super().__init__()
		self.data = {}
		for (destination, source) in keys.items():
			self.set(row, source, destination)
	
	def dump(self):
		return {k: v for (k, v) in self.data.items() if v}



class VariantHolder:
	"""Base class only, do not instantiate"""
	
	def __init__(self, definition, keys):
		self.definition = definition
		self.entries = []
		self.keys = keys
	
	# TODO use raw_rows
	def find_variant(self, cell):
		try:
			ref_match = ref_pattern.match(cell)
		except TypeError:
			# in some cases it can be an empty list. TODO are we sure this is the right behaviour?
			return None
		if not ref_match:
			# no variant specified for reuse, so tell the calling method to just do default
			# behaviour
			return None
		
		# pick out the appropriate entry
		ref_index = ref_match.group(1)
		filter_variant = self.get_variant_filter(ref_index)
		b = first(self.entries, filter_variant)
		return b
	
	def get_def(self, row):
		return getattr(row, self.definition)
	
	@staticmethod
	def get_variant_filter(variant_to_use):
		def filter_variant(e):
			field = get_field(e, "variant")
			return field == variant_to_use
		
		return filter_variant


class Translations(VariantHolder):
	def add(self, row):
		entry = self.find_variant(self.get_def(row))
		
		if not entry:
			# there's no @X in the definition, so add a new entry
			entry = TranslationWords(self.get_def(row), getattr(row, self.keys["variant"]),
			                         self.keys)
			self.entries.append(entry)
		
		entry.add(row)
	
	def dump(self):
		return [e.dump() for e in self.entries]


class TranslationWords(VariantHolder):
	def __init__(self, definition, variant, keys):
		self.variant = variant
		super().__init__(definition, keys)
	
	def add(self, row):
		self.entries.append({key: self.get_row_attr(row, key) for key in self.keys})
	
	def get_row_attr(self, row, key):
		row_key = self.keys[key]
		if not row_key:
			row_key = key
			
		try:
			# is it callable?
			value = row_key(row)
		except TypeError:
			# it is not callable
			value = getattr(row, row_key)
				
		entry = self.find_variant(value)
		if entry:
			return entry[row_key]
		else:
			return value
	
	def dump(self):
		dump_dict = self.__dict__.copy()
		del dump_dict["keys"]  # we don't want to include the keys attr in the dump
		del dump_dict["variant"]  # ditto
		dump_dict["entries"] = [{k: v for (k, v) in entry.items() if v}
		                        for entry in dump_dict["entries"]]
		return dump_dict


def main():
	with open("translation.csv", encoding='utf-8') as csv:
		header_row, *rest = csv
		dictionary = Dictionary(rest)
	
	with open("translation.json", "w", encoding='utf-8') as out:
		dictionary.dump(out)


if __name__ == "__main__":
	main()
