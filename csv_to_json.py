import json
import re
import os.path
import itertools

from unidecode import unidecode

# This is the newest version, use this

# TODO we need separate variants for english and dine
# because some dine words have multiple english ones. Notably akeelyei
# FIXME it's using the normalized dine words instead of the accented ones on the dine side of the dictionary

ENGLISH = "english"
NAVAJO = "navajo"
AUDIO_PATH = "/audio/"

# TODO add line numbers
CSV_DIVIDER = "\t"
defaults = ("English word", "Diné word", "No definition provided",
            "No definition provided", None, None)

eng_audio = os.listdir(os.curdir + AUDIO_PATH + ENGLISH)
dine_audio = os.listdir(os.curdir + AUDIO_PATH + NAVAJO)

reuse_pattern = re.compile(r"@(\d)$")


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
	return unidecode(accented_string).replace("'", "").lower()


def get_audio(lang, word):
	audio_path = normalize(word) + ".mp3"
	if audio_path in eng_audio:
		return AUDIO_PATH + lang + "/" + audio_path
	return ""


def get_field(e, field):
	try:
		return getattr(e, field)
	except AttributeError:
		return e[field]
	
	
def get_reference(text):
	return re.match(reuse_pattern, text).group(1)

class Row:
	def __init__(self, row):
		(self.english,
		 self.variant,
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


class Dictionary:
	def __init__(self, lines):
		self.english = {}
		self.navajo = {}
		
		rows = [Row(line.strip("\n").split(CSV_DIVIDER)) for line in lines]
		
		eng_rows = itertools.groupby(rows, lambda r: r.english)
		navajo_rows = itertools.groupby(rows, lambda r: r.navajo)
		
		for (eng_word, word_rows) in eng_rows:
			key = normalize(eng_word)
			entry = EngToDine(key)
			
			# sort to ensure that we don't reference variants we haven't seen yet
			sorted_word_rows = sorted(word_rows, key=lambda r: r.variant)
			
			for row in sorted_word_rows:
				entry.add(row)
			self.english[eng_word] = entry
			
		for (navajo_word, word_rows) in navajo_rows:
			key = normalize(navajo_word)
			entry = DineToEng(key)
			
			# sort to ensure that we don't reference variants we haven't seen yet
			sorted_word_rows = sorted(word_rows, key=lambda r: r.variant)
			
			for row in sorted_word_rows:
				entry.add(row)
			self.navajo[navajo_word] = entry
	
	def dump(self, out):
		english = {k: e.dump() for (k, e) in self.english.items()}
		navajo = {k: e.dump() for (k, e) in self.navajo.items()}
		json.dump({"entries": {"english": english, "navajo": navajo}},
		          out, indent=2, ensure_ascii=False)


# TODO EngToDine and DineToEng can still be merged I think
class EngToDine:
	keys = {
		"word": "navajo",
		"variant": None,  # None means "just use the key". e.g. here look for "variant"
		"literal": None,
		"comment": None,
		"see_also": "see_also_navajo"
	}
	
	def __init__(self, word):
		self.word = word
		self.definition = ""
		self.sentence = ""
		self.phonetic = ""
		self.audio = ""
		self.see_also = []
		self.short_translations = []
		self.translations = Translations("def_navajo", self.keys)
	
	def add(self, row):
		if not reuse_pattern.match(row.def_eng):
			self.definition = row.def_eng
		if not reuse_pattern.match(row.sentence_eng):
			self.sentence = row.sentence_eng
		if not reuse_pattern.match(row.phonetic_eng):
			self.phonetic = row.phonetic_eng
		if not reuse_pattern.match(row.see_also_eng):
			self.see_also = [normalize(sa) for sa in row.see_also_eng.split(", ") if sa]
		
		self.audio = get_audio(ENGLISH, row.english)
		
		self.short_translations.append(row.navajo)
		self.translations.add(row)
	
	def dump(self):
		out = {k: v for (k, v) in self.__dict__.items() if v}
		out["translations"] = self.translations.dump()
		return out


class DineToEng:
	keys = {
		"word": "english",
		"variant": None,  # None means "just use the key". e.g. here look for "variant"
		"comment": None,
		"see_also": "see_also_eng"
	}
	
	def __init__(self, word):
		self.word = word
		self.definition = ""
		self.literal = ""
		self.sentence = ""
		self.phonetic = ""
		self.audio = ""
		self.see_also = []
		self.short_translations = []
		self.translations = Translations("def_eng", self.keys)
	
	def add(self, row):
		if not reuse_pattern.match(row.def_navajo):
			self.definition = row.def_navajo
		if not reuse_pattern.match(row.literal):
			self.literal = row.literal
		if not reuse_pattern.match(row.sentence_navajo):
			self.sentence = row.sentence_navajo
		if not reuse_pattern.match(row.phonetic_navajo):
			self.phonetic = row.phonetic_navajo
		if not reuse_pattern.match(row.see_also_navajo):
			self.see_also = [normalize(sa) for sa in row.see_also_navajo.split(", ") if sa]
		
		self.audio = get_audio(NAVAJO, row.navajo)
		
		self.short_translations.append(row.english)
		self.translations.add(row)
	
	def dump(self):
		out = {k: v for (k, v) in self.__dict__.items() if v}
		out["translations"] = self.translations.dump()
		return out


class VariantHolder:
	"""Base class only, do not instantiate"""

	def __init__(self, definition, keys):
		self.definition = definition
		self.entries = []
		self.keys = keys
		
	def find_variant(self, cell):
		reuse_match = reuse_pattern.match(cell)
		if reuse_match:
			# pick out the appropriate entry
			variant_to_use = reuse_match.group(1)
			filter_variant = self.get_variant_filter(variant_to_use)
			return first(self.entries, filter_variant)
		else:
			# no variant specified for reuse, so tell the calling method to just do default behaviour
			return None
	
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
			entry = TranslationWords(self.get_def(row), row.variant, self.keys)
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
		value = getattr(row, row_key)
		
		entry = self.find_variant(value)
		if entry:
			return entry[row_key]
		else:
			return value
		
	def dump(self):
		dump_dict = self.__dict__.copy()
		del dump_dict["keys"]  # we don't want to include the keys attr in the dump
		del dump_dict["variant"]  # we don't want to include the keys attr in the dump=
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
